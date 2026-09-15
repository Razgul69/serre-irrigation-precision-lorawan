"""Script de diagnostic pour sonde Vaisala HMP60 sur port série."""
import sys
import time
import serial
import serial.tools.list_ports

def scan_ports():
    print("=== Ports série disponibles sur le système ===")
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("Aucun port série détecté.")
    for p in ports:
        print(f"  - {p.device} : {p.description} [{p.hwid}]")
    print()

def test_vaisala(port="COM7"):
    baudrates = [4800, 19200, 9600, 2400, 115200]
    configs = [
        (8, serial.PARITY_NONE, 1), # 8N1
        (7, serial.PARITY_EVEN, 1), # 7E1
    ]
    commands = [b"?\r\n", b"SEND\r\n", b"R\r\n", b"VERS\r\n", b"HELP\r\n", b"\r\n"]

    print(f"=== Test de communication Vaisala sur {port} ===")
    for baud in baudrates:
        for data_bits, parity, stop_bits in configs:
            parity_str = 'N' if parity == serial.PARITY_NONE else 'E'
            cfg_desc = f"{baud} bauds {data_bits}{parity_str}{stop_bits}"
            try:
                with serial.Serial(port, baudrate=baud, bytesize=data_bits,
                                   parity=parity, stopbits=stop_bits,
                                   timeout=0.6, write_timeout=1.0) as ser:
                    # Clear buffers
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()

                    # Test commands
                    for cmd in commands:
                        ser.write(cmd)
                        time.sleep(0.3)
                        resp = ser.read(256)
                        if resp:
                            print(f"\n[SUCCÈS] Réponse reçue en {cfg_desc} pour commande {cmd.strip()!r} :")
                            print(f"  ASCII: {resp.decode('ascii', errors='replace').strip()}")
                            print(f"  HEX  : {' '.join(f'{b:02X}' for b in resp)}")
                            return True
            except serial.SerialException as e:
                print(f"Erreur d'accès au port {port} ({cfg_desc}): {e}")
                return False
            except Exception as e:
                pass
    print(f"\nAucune réponse reçue sur {port} avec les configurations standard Vaisala.")
    return False

if __name__ == "__main__":
    scan_ports()
    target_port = sys.argv[1] if len(sys.argv) > 1 else "COM7"
    test_vaisala(target_port)
