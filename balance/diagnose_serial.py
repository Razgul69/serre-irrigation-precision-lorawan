"""Sonde de diagnostic de la balance Ohaus (RS232) : écoute passive puis commandes SICS."""
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM3"

def hexdump(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)

with serial.Serial(PORT, 9600, bytesize=8, parity=serial.PARITY_NONE,
                   stopbits=1, timeout=0.5) as ser:
    print(f"Port {PORT} ouvert : 9600 8N1")

    print("\n--- Ecoute passive 5 s (mode impression continue eventuel) ---")
    end = time.monotonic() + 5
    buf = b""
    while time.monotonic() < end:
        chunk = ser.read(256)
        if chunk:
            buf += chunk
    if buf:
        print(f"{len(buf)} octets recus")
        print("HEX  :", hexdump(buf[:200]))
        print("ASCII:", buf[:200].decode("ascii", errors="replace"))
    else:
        print("Aucune donnee spontanee")

    for cmd in (b"SI\r\n", b"S\r\n"):
        ser.reset_input_buffer()
        ser.write(cmd)
        print(f"\n--- Envoi {cmd!r} ---")
        time.sleep(1.0)
        resp = ser.read(256)
        if resp:
            print("HEX  :", hexdump(resp))
            print("ASCII:", resp.decode("ascii", errors="replace"))
        else:
            print("Pas de reponse")
