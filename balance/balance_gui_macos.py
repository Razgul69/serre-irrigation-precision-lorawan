"""Collecteur macOS pour balance Ohaus DP15/M, CSV local uniquement.

Construction sur le Mac :
    python3 -m PyInstaller --windowed --name BalanceCollecteurMac balance_gui_macos.py
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import serial
from serial.tools import list_ports

BAUD = 9600
INTERVAL_S = 5.0
RE_WEIGHT = re.compile(r"^S\s+([SD])\s+([+-]?\d+(?:\.\d+)?)\s+(\S+)\s*$")
UNIT_TO_G = {"g": 1.0, "kg": 1000.0, "mg": 0.001}


def serial_ports() -> list[str]:
    prefixes = ("/dev/cu.usb", "/dev/cu.SLAB", "/dev/cu.wch", "/dev/tty.usb")
    ports = [port.device for port in list_ports.comports()]
    return [port for port in ports if port.startswith(prefixes)]


def data_directory() -> Path:
    return Path.home() / "Documents" / "BalanceCollecteur" / "data balance"


def parse_frame(frame: str):
    frame = frame.strip()
    if not frame:
        return None, None, "vide"
    match = RE_WEIGHT.match(frame)
    if match:
        stable = match.group(1) == "S"
        factor = UNIT_TO_G.get(match.group(3))
        if factor is None:
            return None, stable, f"unite inconnue: {match.group(3)}"
        return float(match.group(2)) * factor, stable, "ok"
    if frame in ("S +", "S+"):
        return None, None, "surcharge"
    if frame in ("S -", "S-"):
        return None, None, "sous-charge"
    return None, None, f"trame inconnue: {frame!r}"


class Collector(threading.Thread):
    def __init__(self, port: str, events: queue.Queue):
        super().__init__(daemon=True)
        self.port = port
        self.events = events
        self.stop_flag = threading.Event()

    def run(self):
        outdir = data_directory()
        outdir.mkdir(parents=True, exist_ok=True)
        csv_path = outdir / f"balance_{dt.datetime.now():%Y%m%d_%H%M%S}.csv"
        last_written: float | None = None
        n_ok = n_err = 0
        try:
            with serial.Serial(self.port, BAUD, bytesize=8, parity=serial.PARITY_NONE,
                               stopbits=1, timeout=2) as ser, \
                 open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["timestamp_utc", "monotonic_s", "raw_frame",
                                 "weight_g", "stable", "status"])
                self.events.put(("info", f"Collecte demarree ({csv_path.name})"))
                while not self.stop_flag.is_set():
                    next_read = time.monotonic() + INTERVAL_S
                    ser.reset_input_buffer()
                    ser.write(b"S\r\n")
                    raw = ser.read_until(b"\n", 64)
                    timestamp = dt.datetime.now(dt.timezone.utc)
                    frame = raw.decode("ascii", errors="replace").strip()
                    weight, stable, status = parse_frame(frame)
                    changed = weight is not None and weight != last_written

                    if changed or weight is None:
                        writer.writerow([timestamp.isoformat(), f"{time.monotonic():.2f}", frame,
                                         "" if weight is None else f"{weight:.3f}",
                                         "" if stable is None else int(stable), status])
                        csv_file.flush()
                    if status == "ok":
                        n_ok += 1
                        self.events.put(("weight", weight, n_ok, n_err))
                    else:
                        n_err += 1
                        self.events.put(("error", status, n_ok, n_err))
                    if changed:
                        last_written = weight
                    self.stop_flag.wait(max(0.0, next_read - time.monotonic()))
        except serial.SerialException as error:
            self.events.put(("fatal", f"Erreur port serie : {error}"))
            return
        self.events.put(("info", f"Collecte arretee ({n_ok} ok, {n_err} erreurs)"))


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Balance Ohaus - Collecte Mac")
        self.root.geometry("430x270")
        self.root.resizable(False, False)
        self.collector: Collector | None = None
        self.events: queue.Queue = queue.Queue()
        self.caffeinate: subprocess.Popen | None = None

        self.lbl_weight = tk.Label(self.root, text="--- g", font=("Helvetica", 32, "bold"))
        self.lbl_weight.pack(pady=(15, 3))
        self.lbl_status = tk.Label(self.root, text="Arrete", font=("Helvetica", 11), fg="grey")
        self.lbl_status.pack()
        self.lbl_counts = tk.Label(self.root, text="", font=("Helvetica", 9), fg="grey")
        self.lbl_counts.pack()

        port_frame = tk.Frame(self.root)
        port_frame.pack(pady=(12, 4))
        tk.Label(port_frame, text="Port balance :").pack(side=tk.LEFT, padx=(0, 8))
        self.port_var = tk.StringVar()
        self.port_menu = ttk.Combobox(port_frame, textvariable=self.port_var,
                                      state="readonly", width=32)
        self.port_menu.pack(side=tk.LEFT)
        self.refresh_ports()

        controls = tk.Frame(self.root)
        controls.pack(pady=14)
        self.btn_start = tk.Button(controls, text="MARCHE", width=12, height=2,
                                   bg="#2e7d32", fg="white",
                                   font=("Helvetica", 11, "bold"), command=self.start)
        self.btn_start.pack(side=tk.LEFT, padx=10)
        self.btn_stop = tk.Button(controls, text="ARRET", width=12, height=2,
                                  bg="#c62828", fg="white",
                                  font=("Helvetica", 11, "bold"), command=self.stop,
                                  state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(200, self.poll_events)

    def refresh_ports(self):
        ports = serial_ports()
        self.port_menu["values"] = ports
        self.port_var.set(ports[0] if len(ports) == 1 else "")
        if not ports:
            self.lbl_status.config(text="Branchez la balance USB puis relancez l'application", fg="#c62828")

    def start(self):
        port = self.port_var.get()
        if not port:
            self.refresh_ports()
            return
        self.caffeinate = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
        self.collector = Collector(port, self.events)
        self.collector.start()
        self.port_menu.config(state=tk.DISABLED)
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.lbl_status.config(text="Collecte en cours - veille Mac bloquee", fg="#2e7d32")

    def stop(self):
        if self.collector:
            self.collector.stop_flag.set()
        if self.caffeinate:
            self.caffeinate.terminate()
            self.caffeinate = None
        self.port_menu.config(state="readonly")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.lbl_status.config(text="Arrete", fg="grey")

    def poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "weight":
                    _, weight, n_ok, n_err = event
                    self.lbl_weight.config(text=f"{weight:.1f} g")
                    self.lbl_counts.config(text=f"{n_ok} mesures, {n_err} erreurs")
                elif event[0] == "error":
                    _, message, n_ok, n_err = event
                    self.lbl_counts.config(text=f"{n_ok} mesures, {n_err} erreurs - {message}")
                elif event[0] == "fatal":
                    self.stop()
                    self.lbl_status.config(text=event[1], fg="#c62828")
                else:
                    self.lbl_status.config(text=event[1])
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