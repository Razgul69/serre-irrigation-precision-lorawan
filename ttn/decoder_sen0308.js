// Décodeur TTN v3 — Nano ESP32 + DFRobot SEN0308 (uplink port 3)
// Payload : [mV(2) | index_x10(2) | vwc_x10(2)]  — vwc = 0xFFFF si calibration gravimétrique absente
function decodeUplink(input) {
    var b = input.bytes;
    var vwcRaw = (b[4] << 8) | b[5];
    var data = {
        sen0308_mv: (b[0] << 8) | b[1],
        sen0308_index_pct: ((b[2] << 8) | b[3]) / 10.0
    };
    if (vwcRaw !== 0xFFFF) data.sen0308_vwc_pct = vwcRaw / 10.0;
    return { data: data };
}
