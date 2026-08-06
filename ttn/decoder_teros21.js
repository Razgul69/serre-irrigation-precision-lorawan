// Décodeur TTN v3 — Dragino SDI-12-LB + METER TEROS21
// Le TEROS21 renvoie via SDI-12 : potentiel matriciel (kPa, négatif) et température (°C)
// Adapter le parsing au format exact configuré dans le Dragino (mode payload ASCII SDI-12)
function decodeUplink(input) {
    var bytes = input.bytes;
    // Payload Dragino SDI-12-LB : batterie (2 octets) + réponse SDI-12 en ASCII
    var batteryMv = (bytes[0] << 8) | bytes[1];
    var ascii = "";
    for (var i = 2; i < bytes.length; i++) ascii += String.fromCharCode(bytes[i]);
    // Réponse type TEROS21 : "0+-40.5+22.3" => adresse, potentiel, température
    var m = ascii.match(/([+-]?\d+\.?\d*)\+?([+-]?\d+\.?\d*)$/);
    var data = { battery_v: batteryMv / 1000.0, raw_sdi12: ascii };
    if (m) {
        data.matric_potential_kpa = parseFloat(m[1]);
        data.soil_temp_c = parseFloat(m[2]);
    }
    return { data: data };
}
