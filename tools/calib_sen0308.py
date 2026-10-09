"""Calibration DFRobot SEN0308 via Arduino Nano ESP32 (firmware esp32_nano_sen0308).

Modes :
  python calib_sen0308.py --port COM5                       # enregistre le CSV serie (+ InfluxDB optionnel)
  python calib_sen0308.py --port COM5 --ref air             # capture 30 s dans l'air -> AIR_MV
  python calib_sen0308.py --port COM5 --ref water           # capture 30 s dans l'eau -> WATER_MV
  python calib_sen0308.py --fit points.csv [--deg 2]        # ajuste theta = f(mV) (niveau 2)

Fichier points.csv (niveau 2) : colonnes  mv,theta_pct   (une ligne par couple mesure)
Protocole complet : docs/calibration_sen0308.md
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "balance"))
from collect_balance import influx_write  # noqa: E402  (meme ecriture InfluxDB que la balance)


def load_token() -> str:
    env = HERE.parent / "server" / ".env"
    if env.exists():
        for ln in env.read_text().splitlines():
            if ln.startswith("INFLUX_TOKEN="):
                return ln.split("=", 1)[1].strip()
    return ""


def record(args) -> int:
    import serial

    outdir = HERE.parent / "data sen0308"
    outdir.mkdir(exist_ok=True)
    csv_path = outdir / f"sen0308_{args.sensor_id}_{dt.datetime.now():%Y%m%d_%H%M%S}.csv"
    token = "" if args.no_influx else load_token()
    if not args.no_influx and not token:
        print("Token InfluxDB introuvable (server/.env) : passage en mode CSV seul", file=sys.stderr)
        args.no_influx = True

    with serial.Serial(args.port, 115200, timeout=2) as ser, \
         open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_utc", "millis_ms", "mv", "index_pct", "vwc_pct"])
        time.sleep(2)
        ser.reset_input_buffer()
        if args.ref:
            ser.write(b"a" if args.ref == "air" else b"w")
        print(f"Enregistrement {args.port} -> {csv_path}  (Ctrl+C pour arreter)")
        n = 0
        try:
            while True:
                line = ser.readline().decode("ascii", errors="replace").strip()
                if not line:
                    continue
                if line.startswith("#"):
                    print(line)
                    if args.ref and "_MV =" in line:
                        return 0
                    continue
                parts = line.split(",")
                if len(parts) < 3 or not parts[1].replace(".", "").isdigit():
                    continue
                ts = dt.datetime.now(dt.timezone.utc)
                w.writerow([ts.isoformat()] + parts[:4] + [""] * (4 - len(parts)))
                f.flush()
                n += 1
                if not args.no_influx:
                    fields = f"mv={float(parts[1])},index_pct={float(parts[2])}"
                    if len(parts) > 3 and parts[3]:
                        fields += f",vwc_pct={float(parts[3])}"
                    err = influx_write(args.influx_url, args.influx_org, args.influx_bucket, token,
                                       f"sen0308,sensor_id={args.sensor_id} {fields} "
                                       f"{int(ts.timestamp() * 1e9)}")
                    if err and n == 1:
                        print(f"InfluxDB inaccessible ({err}) - le CSV continue", file=sys.stderr)
                if n % 60 == 0:
                    print(f"[{ts:%H:%M:%S}] {n} mesures, derniere {parts[1]} mV / {parts[2]} %")
        except KeyboardInterrupt:
            print(f"\nArret. {n} mesures. CSV : {csv_path}")
    return 0


def fit(args) -> int:
    import numpy as np

    rows = list(csv.DictReader(open(args.fit, encoding="utf-8")))
    mv = np.array([float(r["mv"]) for r in rows])
    th = np.array([float(r["theta_pct"]) for r in rows])
    if len(mv) < args.deg + 2:
        print(f"Il faut au moins {args.deg + 2} points pour un degre {args.deg}", file=sys.stderr)
        return 2
    coef = np.polyfit(mv, th, args.deg)
    pred = np.polyval(coef, mv)
    resid = th - pred
    r2 = 1 - np.sum(resid**2) / np.sum((th - th.mean())**2)
    print(f"Ajustement degre {args.deg} sur {len(mv)} points : R^2 = {r2:.4f}, "
          f"residu max = {np.abs(resid).max():.2f} % vol")
    if args.deg == 1:
        print(f"  CR1000  : Const SEN_A = {coef[0]:.6f}   Const SEN_B = {coef[1]:.3f}")
        print(f"  config.h: #define VWC_A ({coef[0]:.6f}f)   #define VWC_B ({coef[1]:.3f}f)")
    else:
        print("  coefficients (puissance decroissante) :", ", ".join(f"{c:.6g}" for c in coef))
    print("  Criteres : R^2 >= 0.95 et residus < 3 % vol" + ("  -> OK" if r2 >= 0.95 and np.abs(resid).max() < 3 else "  -> a revoir"))
    for m, t, p_ in zip(mv, th, pred):
        print(f"    {m:7.0f} mV  mesure {t:5.1f} %  ajuste {p_:5.1f} %  ecart {t - p_:+5.1f}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Calibration SEN0308 (Nano ESP32)")
    ap.add_argument("--port", default="COM5")
    ap.add_argument("--sensor-id", default="sen1")
    ap.add_argument("--ref", choices=["air", "water"], help="capture de reference 30 s puis quitte")
    ap.add_argument("--fit", metavar="CSV", help="ajuste theta = f(mV) sur un CSV mv,theta_pct")
    ap.add_argument("--deg", type=int, default=1, choices=[1, 2])
    ap.add_argument("--no-influx", action="store_true")
    ap.add_argument("--influx-url", default="http://localhost:8086")
    ap.add_argument("--influx-org", default="ird")
    ap.add_argument("--influx-bucket", default="sondes")
    args = ap.parse_args()
    return fit(args) if args.fit else record(args)


if __name__ == "__main__":
    sys.exit(main())
