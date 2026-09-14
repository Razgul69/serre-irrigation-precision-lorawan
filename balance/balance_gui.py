"""Interface Marche/Arret pour la collecte de la balance Ohaus DP15/M.

- Marche : ouvre COM3, interroge la balance (commande SICS "S"), ecrit un CSV
  dans "data balance" et pousse le poids vers InfluxDB local.
- Tant que la collecte tourne, la mise en veille du PC est bloquee
  (SetThreadExecutionState) ; l'ecran peut s'eteindre.

Construction de l'exe :
    pyinstaller --onefile --noconsole --name BalanceCollecteur balance/balance_gui.py
"""
from __future__ import annotations

import csv
import ctypes
import datetime as dt
import queue
import re
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from pathlib import Path

import serial

PORT = "COM3"
BAUD = 9600
INTERVAL_S = 5.0
INFLUX_URL = "http://localhost:8086"
INFLUX_ORG = "ird"
INFLUX_BUCKET = "sondes"
BALANCE_ID = "dp15m"

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

RE_WEIGHT = re.compile(r"^S\s+([SD])\s+([+-]?\d+(?:\.\d+)?)\s+(\S+)\s*$")
UNIT_TO_G = {"g": 1.0, "kg": 1000.0, "mg": 0.001}


def project_root() -> Path:
    """Racine du projet : dossier de l'exe (gele) ou parent du dossier balance/."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def read_influx_token(root: Path) -> str:
    env = root / "server" / ".env"
    if env.exists():
        for ln in env.read_text().splitlines():
            if ln.startswith("INFLUX_TOKEN="):
                return ln.split("=", 1)[1].strip()
    return ""


def parse_frame(frame: str):
    frame = frame.strip()
    if not frame:
        return None, None, "vide"
    m = RE_WEIGHT.match(frame)
    if m:
        stable = m.group(1) == "S"
        factor = UNIT_TO_G.get(m.group(3))
        if factor is None:
            return None, stable, f"unite inconnue: {m.group(3)}"
        return float(m.group(2)) * factor, stable, "ok"
    if frame in ("S +", "S+"):
        return None, None, "surcharge"
    if frame in ("S -", "S-"):
        return None, None, "sous-charge"
    return None, None, f"trame inconnue: {frame!r}"


def influx_write(token: str, line: str) -> str | None:
    url = f"{INFLUX_URL}/api/v2/write?org={INFLUX_ORG}&bucket={INFLUX_BUCKET}&precision=ns"
    req = urllib.request.Request(
        url, data=line.encode(), method="POST",
        headers={"Authorization": f"Token {token}",
                 "Content-Type": "text/plain; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=5):
            return None
    except (urllib.error.URLError, OSError) as e:
        return str(e)


class Collector(threading.Thread):
    def __init__(self, events: queue.Queue):
        super().__init__(daemon=True)
        self.events = events
        self.stop_flag = threading.Event()

    def run(self):
        root = project_root()
        token = read_influx_token(root)
        outdir = root / "data balance"
        outdir.mkdir(parents=True, exist_ok=True)
        csv_path = outdir / f"balance_{dt.datetime.now():%Y%m%d_%H%M%S}.csv"
        influx_warned = False
        n_ok = n_err = 0
        last_written: float | None = None
        try:
            with serial.Serial(PORT, BAUD, bytesize=8, parity=serial.PARITY_NONE,
                               stopbits=1, timeout=2) as ser, \
                 open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp_utc", "monotonic_s", "raw_frame",
                                 "weight_g", "stable", "status"])
                self.events.put(("info", f"Collecte demarree ({csv_path.name})"))
                while not self.stop_flag.is_set():
                    t_next = time.monotonic() + INTERVAL_S
                    ser.reset_input_buffer()
                    ser.write(b"S\r\n")
                    raw = ser.read_until(b"\n", 64)
                    ts = dt.datetime.now(dt.timezone.utc)
                    frame = raw.decode("ascii", errors="replace").strip()
                    weight, stable, status = parse_frame(frame)
                    changed = weight is not None and weight != last_written
                    if changed or weight is None:
                        writer.writerow([ts.isoformat(), f"{time.monotonic():.2f}", frame,
                                         "" if weight is None else f"{weight:.3f}",
                                         "" if stable is None else int(stable), status])
                        f.flush()
                    if status == "ok":
                        n_ok += 1
                        self.events.put(("weight", weight, n_ok, n_err))
                    else:
                        n_err += 1
                        self.events.put(("error", f"{status}", n_ok, n_err))
                    if changed and token:
                        ns = int(ts.timestamp() * 1e9)
                        line = (f"balance,balance_id={BALANCE_ID}"
                                f" weight_g={weight},stable={int(bool(stable))}i {ns}")
                        err = influx_write(token, line)
                        if err and not influx_warned:
                            self.events.put(("info", "InfluxDB inaccessible - CSV seul"))
                            influx_warned = True
                        elif not err:
                            influx_warned = False
                    if changed:
                        last_written = weight
                    self.stop_flag.wait(max(0.0, t_next - time.monotonic()))
        except serial.SerialException as e:
            self.events.put(("fatal", f"Erreur port serie : {e}"))
            return
        self.events.put(("info", f"Collecte arretee ({n_ok} ok, {n_err} erreurs)"))


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Balance Ohaus - Collecte")
        self.root.geometry("360x230")
        self.root.resizable(False, False)
        self.collector: Collector | None = None
        self.events: queue.Queue = queue.Queue()

        self.lbl_weight = tk.Label(self.root, text="--- g", font=("Segoe UI", 32, "bold"))
        self.lbl_weight.pack(pady=(15, 5))
        self.lbl_status = tk.Label(self.root, text="Arrete", font=("Segoe UI", 11), fg="grey")
        self.lbl_status.pack()
        self.lbl_counts = tk.Label(self.root, text="", font=("Segoe UI", 9), fg="grey")
        self.lbl_counts.pack()

        frame = tk.Frame(self.root)
        frame.pack(pady=15)
        self.btn_start = tk.Button(frame, text="MARCHE", width=12, height=2,
                                   bg="#2e7d32", fg="white",
                                   font=("Segoe UI", 11, "bold"), command=self.start)
        self.btn_start.pack(side=tk.LEFT, padx=10)
        self.btn_stop = tk.Button(frame, text="ARRET", width=12, height=2,
                                  bg="#c62828", fg="white",
                                  font=("Segoe UI", 11, "bold"), command=self.stop,
                                  state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(200, self.poll_events)

    def start(self):
        if self.collector and self.collector.is_alive():
            return
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        self.collector = Collector(self.events)
        self.collector.start()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.lbl_status.config(text="Collecte en cours - veille PC bloquee", fg="#2e7d32")

    def stop(self):
        if self.collector:
            self.collector.stop_flag.set()
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.lbl_status.config(text="Arrete", fg="grey")

    def poll_events(self):
        try:
            while True:
                ev = self.events.get_nowait()
                if ev[0] == "weight":
                    _, w, n_ok, n_err = ev
                    self.lbl_weight.config(text=f"{w:.1f} g")
                    self.lbl_counts.config(text=f"{n_ok} mesures, {n_err} erreurs")
                elif ev[0] == "error":
                    _, msg, n_ok, n_err = ev
                    self.lbl_counts.config(text=f"{n_ok} mesures, {n_err} erreurs - {msg}")
                elif ev[0] == "fatal":
                    self.lbl_status.config(text=ev[1], fg="#c62828")
                    self.stop()
                else:
                    self.lbl_status.config(text=ev[1],
                                           fg="#2e7d32" if self.btn_stop["state"] == tk.NORMAL else "grey")
        except queue.Empty:
            pass
        self.root.after(200, self.poll_events)

    def on_close(self):
        self.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
