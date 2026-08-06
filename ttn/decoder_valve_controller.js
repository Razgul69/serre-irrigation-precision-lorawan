// Décodeur TTN v3 — Contrôleur de vanne ESP32 (uplink port 2)
// Payload : [état(1) | volume_cycle_mL(4) | volume_total_L_x10(2) | uptime_min(2)]
function decodeUplink(input) {
  var b = input.bytes;
  return {
    data: {
      valve_open: b[0] === 1,
      cycle_volume_ml: (b[1] << 24) | (b[2] << 16) | (b[3] << 8) | b[4],
      total_volume_l: ((b[5] << 8) | b[6]) / 10.0,
      uptime_min: (b[7] << 8) | b[8]
    }
  };
}

// Encodeur downlink (port 1)
// { "command": "open" } | { "command": "close" } | { "command": "open", "volume_ml": 5000 }
function encodeDownlink(input) {
  var d = input.data;
  if (d.command === "close") return { bytes: [0x00], fPort: 1 };
  if (d.command === "open" && d.volume_ml) {
    var v = Math.round(d.volume_ml / 100);
    return { bytes: [0x02, (v >> 8) & 0xff, v & 0xff], fPort: 1 };
  }
  return { bytes: [0x01], fPort: 1 };
}
