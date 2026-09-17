"""Diagnostic direct de la balance Ohaus sur macOS, sans interface ni Docker."""
from __future__ import annotations

import sys
import time

import serial
from serial.tools import list_ports


def candidate_ports():
    prefixes = ("/dev/cu.usb", "/dev/cu.SLAB", "/dev/cu.wch", "/dev/tty.usb")
    return [port for port in list_ports.comports()
            if port.device.startswith(prefixes)]


ports = candidate_ports()
print("Ports serie USB detectes :")
for port in ports:
    print(f"  {port.device} | {port.description} | {port.hwid}")

if not ports:
    raise SystemExit("Aucun port USB serie. Verifier adaptateur, cable et pilote.")

port_name = sys.argv[1] if len(sys.argv) > 1 else ports[0].device
print(f"\nTest de {port_name} en 9600 8N1. Arret : Ctrl+C")

with serial.Serial(port_name, 9600, bytesize=8, parity=serial.PARITY_NONE,
                   stopbits=1, timeout=2) as connection:
    sequence = 0
    while True:
        sequence += 1
        connection.reset_input_buffer()
        connection.write(b"S\r\n")
        connection.flush()
        raw = connection.read_until(b"\n", 64)
        now = time.strftime("%H:%M:%S")
        hex_data = " ".join(f"{byte:02X}" for byte in raw) or "(aucun octet)"
        text = raw.decode("ascii", errors="replace").strip() or "(timeout)"
        print(f"[{now}] #{sequence} HEX={hex_data} ASCII={text}", flush=True)
        time.sleep(3)