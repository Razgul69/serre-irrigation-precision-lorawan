"""Collecteur balance Ohaus DP15/M (protocole SICS) sur port serie.

Interroge la balance avec la commande "S" (poids stable), journalise chaque
trame brute en CSV et pousse le poids vers InfluxDB v2 (optionnel).

Usage :
    python collect_balance.py                 # config par defaut (balance.yaml si present)
    python collect_balance.py --port COM3 --interval 5 --no-influx
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import serial

# Reponse SICS : "S S    1234.5 g" (stable), "S D ..." (dynamique),
# "S +"/"S -" (sur/sous-charge), "ES" (erreur de syntaxe)
RE_WEIGHT = re.compile(r"^S\s+([SD])\s+([+-]?\d+(?:\.\d+)?)\s+(\S+)\s*$")

UNIT_TO_G = {"g": 1.0, "kg": 1000.0, "mg": 0.001}


def parse_frame(frame: str):
    """Retourne (poids_g, stable, status)."""
    frame = frame.strip()
    if not frame:
        return None, None, "empty"
    m = RE_WEIGHT.match(frame)
    if m:
        stable = m.group(1) == "S"
        value = float(m.group(2))
        factor = UNIT_TO_G.get(m.group(3))
        if factor is None:
            return None, stable, f"unite_inconnue:{m.group(3)}"
        return value * factor, stable, "ok"
    if frame in ("S +", "S+"):
        return None, None, "surcharge"
    if frame in ("S -", "S-"):
        return None, None, "sous_charge"
    if frame == "ES":
        return None, None, "erreur_syntaxe"
    if frame == "S I":
        return None, None, "commande_inexecutable"
    return None, None, "trame_inconnue"


def influx_write(base_url: str, org: str, bucket: str, token: str, line: str) -> str | None:
    url = f"{base_url}/api/v2/write?org={org}&bucket={bucket}&precision=ns"
    req = urllib.request.Request(
        url, data=line.encode(), method="POST",
        headers={"Authorization": f"Token {token}",
                 "Content-Type": "text/plain; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=5):
            return None
    except (urllib.error.URLError, OSError) as e:
        return str(e)


def main() -> int:
    ap = argparse.ArgumentParser(description="Collecteur balance Ohaus (SICS)")
    ap.add_argument("--port", default="COM3")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--interval", type=float, default=5.0, help="secondes entre lectures")
    ap.add_argument("--outdir", default=str(Path(__file__).parent.parent / "data balance"))
    ap.add_argument("--balance-id", default="dp15m")
    ap.add_argument("--no-influx", action="store_true")
    ap.add_argument("--influx-url", default="http://localhost:8086")
    ap.add_argument("--influx-org", default="ird")
    ap.add_argument("--influx-bucket", default="sondes")
    ap.add_argument("--influx-token", default="")
    args = ap.parse_args()

    token = args.influx_token
    if not args.no_influx and not token:
        env = Path(__file__).parent.parent / "server" / ".env"
        if env.exists():
            for ln in env.read_text().splitlines():
                if ln.startswith("INFLUX_TOKEN="):
                    token = ln.split("=", 1)[1].strip()
        if not token:
            print("Token InfluxDB introuvable : --influx-token ou server/.env requis", file=sys.stderr)
            return 2

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / f"balance_{dt.datetime.now():%Y%m%d_%H%M%S}.csv"

    n_ok = n_err = 0
    influx_down_reported = False

    with serial.Serial(args.port, args.baud, bytesize=8, parity=serial.PARITY_NONE,
                       stopbits=1, timeout=2) as ser, \
         open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "monotonic_s", "raw_frame",
                         "weight_g", "stable", "status"])
        print(f"Collecte demarree sur {args.port} toutes les {args.interval}s -> {csv_path}")
        print("Arret : Ctrl+C")

        try:
            while True:
                t_next = time.monotonic() + args.interval
                ser.reset_input_buffer()
                ser.write(b"S\r\n")
                raw = ser.read_until(b"\n", 64)
                ts = dt.datetime.now(dt.timezone.utc)
                mono = time.monotonic()
                frame = raw.decode("ascii", errors="replace").strip()
                weight, stable, status = parse_frame(frame)

                writer.writerow([ts.isoformat(), f"{mono:.2f}", frame,
                                 "" if weight is None else f"{weight:.3f}",
                                 "" if stable is None else int(stable), status])
                f.flush()

                if status == "ok":
                    n_ok += 1
                else:
                    n_err += 1
                    print(f"[{ts:%H:%M:%S}] trame non exploitable ({status}): {frame!r}")

                if weight is not None and not args.no_influx:
                    ns = int(ts.timestamp() * 1e9)
                    line = (f"balance,balance_id={args.balance_id}"
                            f" weight_g={weight},stable={int(bool(stable))}i {ns}")
                    err = influx_write(args.influx_url, args.influx_org,
                                       args.influx_bucket, token, line)
                    if err and not influx_down_reported:
                        print(f"InfluxDB inaccessible ({err}) - le CSV continue", file=sys.stderr)
                        influx_down_reported = True
                    elif not err:
                        influx_down_reported = False

                if n_ok and n_ok % 120 == 0:
                    print(f"[{ts:%H:%M:%S}] {n_ok} mesures ok, {n_err} erreurs, "
                          f"dernier poids {weight} g")

                time.sleep(max(0.0, t_next - time.monotonic()))
        except KeyboardInterrupt:
            print(f"\nArret. {n_ok} mesures ok, {n_err} erreurs. CSV : {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
