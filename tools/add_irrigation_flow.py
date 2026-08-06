# -*- coding: utf-8 -*-
"""Ajoute le flux 'IoT Irrigation Piloté' au flows.json Node-RED existant (CO2 Bridge conservé)."""
import json, io

FLOWS = r"D:\Arduino_PlatformIO\master_v15_2sensors\control_center\observability\nodered\flows.json"

with io.open(FLOWS, "r", encoding="utf-8") as f:
    flows = json.load(f)

# Purge d'une éventuelle version précédente du flux irrigation
flows = [n for n in flows if not (n.get("id", "").startswith("irr_") or n.get("z", "").startswith("irr_tab"))]

TAB = "irr_tab_1"

new_nodes = [
    {"id": TAB, "type": "tab", "label": "IoT Irrigation Piloté", "disabled": False,
     "info": "TEROS21 (Dragino SDI-12) via TTN -> seuils -> downlink vannes ESP32 + dashboard"},

    # --- Config TTN MQTT (renseigner username/password dans l'éditeur) ---
    {"id": "irr_mqtt_broker", "type": "mqtt-broker", "name": "TTN EU1",
     "broker": "eu1.cloud.thethings.network", "port": "8883", "tls": "irr_tls",
     "clientid": "", "autoConnect": True, "usetls": True, "protocolVersion": "4",
     "keepalive": "60", "cleansession": True, "autoUnsubscribe": True,
     "birthTopic": "", "closeTopic": "", "willTopic": "", "sessionExpiry": ""},
    {"id": "irr_tls", "type": "tls-config", "name": "TTN TLS", "cert": "", "key": "",
     "ca": "", "certname": "", "keyname": "", "caname": "", "servername": "", "verifyservercert": True},

    # --- Dashboard ---
    {"id": "irr_ui_base", "type": "ui_base", "theme": {"name": "theme-dark"}, "site": {"name": "Irrigation Serre", "hideToolbar": "false", "allowSwipe": "false", "lockMenu": "false", "allowTempTheme": "true", "dateFormat": "DD/MM/YYYY", "sizes": {"sx": 48, "sy": 48, "gx": 6, "gy": 6, "cx": 6, "cy": 6, "px": 0, "py": 0}}},
    {"id": "irr_ui_tab", "type": "ui_tab", "name": "Irrigation", "icon": "opacity", "order": 1, "disabled": False, "hidden": False},
    {"id": "irr_grp_mesures", "type": "ui_group", "name": "Mesures TEROS21", "tab": "irr_ui_tab", "order": 1, "disp": True, "width": "6"},
    {"id": "irr_grp_seuils", "type": "ui_group", "name": "Seuils d'irrigation", "tab": "irr_ui_tab", "order": 2, "disp": True, "width": "6"},
    {"id": "irr_grp_cmd", "type": "ui_group", "name": "Commande manuelle", "tab": "irr_ui_tab", "order": 3, "disp": True, "width": "6"},
    {"id": "irr_grp_etat", "type": "ui_group", "name": "État vannes & débit", "tab": "irr_ui_tab", "order": 4, "disp": True, "width": "6"},

    # ================= UPLINK TEROS21 =================
    {"id": "irr_mqtt_in_up", "type": "mqtt in", "z": TAB, "name": "TTN uplinks",
     "topic": "v3/+/devices/+/up", "qos": "0", "datatype": "json",
     "broker": "irr_mqtt_broker", "nl": False, "rap": True, "rh": 0, "inputs": 0,
     "x": 140, "y": 100, "wires": [["irr_fn_route"]]},

    {"id": "irr_fn_route", "type": "function", "z": TAB, "name": "Router: TEROS21 / vanne",
     "func": (
        "const devId = msg.payload.end_device_ids.device_id;\n"
        "const dp = msg.payload.uplink_message.decoded_payload || {};\n"
        "msg.device_id = devId;\n"
        "msg.decoded = dp;\n"
        "// Convention de nommage TTN : teros-zoneN..., vanne-zoneN...\n"
        "if (devId.startsWith('teros')) return [msg, null];\n"
        "if (devId.startsWith('vanne')) return [null, msg];\n"
        "return [null, null];\n"),
     "outputs": 2, "noerr": 0, "x": 340, "y": 100,
     "wires": [["irr_fn_teros"], ["irr_fn_vanne_status"]]},

    {"id": "irr_fn_teros", "type": "function", "z": TAB, "name": "Décode TEROS21",
     "func": (
        "// Potentiel matriciel (kPa, négatif) + T° sol depuis le payload Dragino décodé par TTN\n"
        "const d = msg.decoded;\n"
        "const zone = msg.device_id.replace(/^teros-?/, '') || 'zone1';\n"
        "let potentiel = d.matric_potential_kpa;\n"
        "// Fallback : parse de la réponse SDI-12 brute type '0+-40.5+22.3'\n"
        "if (potentiel === undefined && typeof d.raw_sdi12 === 'string') {\n"
        "  const m = d.raw_sdi12.match(/([+-]?\\d+\\.?\\d*)\\+([+-]?\\d+\\.?\\d*)$/);\n"
        "  if (m) { potentiel = parseFloat(m[1]); d.soil_temp_c = parseFloat(m[2]); }\n"
        "}\n"
        "if (potentiel === undefined) return null;\n"
        "const mesure = { zone, potentiel_kpa: potentiel, temp_c: d.soil_temp_c, batterie_v: d.battery_v, ts: Date.now() };\n"
        "const mesures = flow.get('mesures') || {};\n"
        "mesures[zone] = mesure;\n"
        "flow.set('mesures', mesures);\n"
        "msg.payload = mesure;\n"
        "return msg;\n"),
     "outputs": 1, "noerr": 0, "x": 560, "y": 80,
     "wires": [["irr_gauge_pot", "irr_fn_seuils", "irr_fn_influx_soil", "irr_dbg_teros"]]},

    {"id": "irr_dbg_teros", "type": "debug", "z": TAB, "name": "debug matricielle", "active": True,
     "tosidebar": True, "console": False, "tostatus": False, "complete": "payload", "targetType": "msg",
     "x": 790, "y": 40, "wires": []},

    {"id": "irr_gauge_pot", "type": "ui_gauge", "z": TAB, "name": "Potentiel matriciel",
     "group": "irr_grp_mesures", "order": 1, "width": 0, "height": 0, "gtype": "gage",
     "title": "Potentiel matriciel", "label": "kPa", "format": "{{value | number:1}}",
     "min": "-100", "max": "0", "colors": ["#ca3838", "#e6e600", "#00b500"],
     "seg1": "-40", "seg2": "-10", "x": 790, "y": 80, "wires": []},

    # ================= SEUILS (dashboard) =================
    {"id": "irr_num_sec", "type": "ui_numeric", "z": TAB, "name": "Seuil sec",
     "label": "Seuil sec (kPa)", "group": "irr_grp_seuils", "order": 1, "width": 0, "height": 0,
     "wrap": False, "passthru": True, "topic": "seuil_sec", "topicType": "str",
     "format": "{{value}}", "min": "-100", "max": "0", "step": "1",
     "x": 130, "y": 260, "wires": [["irr_fn_set_seuil"]]},
    {"id": "irr_num_humide", "type": "ui_numeric", "z": TAB, "name": "Seuil humide",
     "label": "Seuil humide (kPa)", "group": "irr_grp_seuils", "order": 2, "width": 0, "height": 0,
     "wrap": False, "passthru": True, "topic": "seuil_humide", "topicType": "str",
     "format": "{{value}}", "min": "-100", "max": "0", "step": "1",
     "x": 140, "y": 300, "wires": [["irr_fn_set_seuil"]]},
    {"id": "irr_num_volmax", "type": "ui_numeric", "z": TAB, "name": "Volume max",
     "label": "Volume max (L)", "group": "irr_grp_seuils", "order": 3, "width": 0, "height": 0,
     "wrap": False, "passthru": True, "topic": "volume_max_l", "topicType": "str",
     "format": "{{value}}", "min": "1", "max": "50", "step": "1",
     "x": 140, "y": 340, "wires": [["irr_fn_set_seuil"]]},
    {"id": "irr_sw_auto", "type": "ui_switch", "z": TAB, "name": "Mode auto",
     "label": "Irrigation automatique", "group": "irr_grp_seuils", "order": 4, "width": 0, "height": 0,
     "passthru": True, "topic": "auto", "topicType": "str", "style": "",
     "onvalue": "true", "onvalueType": "bool", "offvalue": "false", "offvalueType": "bool",
     "x": 130, "y": 380, "wires": [["irr_fn_set_seuil"]]},

    {"id": "irr_fn_set_seuil", "type": "function", "z": TAB, "name": "Stocke config",
     "func": (
        "const cfg = flow.get('config') || { seuil_sec: -40, seuil_humide: -10, volume_max_l: 10, auto: false };\n"
        "cfg[msg.topic] = msg.payload;\n"
        "flow.set('config', cfg);\n"
        "node.status({fill:'blue', shape:'dot', text: JSON.stringify(cfg)});\n"
        "return null;\n"),
     "outputs": 1, "noerr": 0, "x": 380, "y": 320, "wires": [[]]},

    # ================= LOGIQUE AUTO =================
    {"id": "irr_fn_seuils", "type": "function", "z": TAB, "name": "Logique seuils -> downlink",
     "func": (
        "const cfg = flow.get('config') || { seuil_sec: -40, seuil_humide: -10, volume_max_l: 10, auto: false };\n"
        "if (!cfg.auto) return null;\n"
        "const m = msg.payload;\n"
        "const etats = flow.get('etats_vannes') || {};\n"
        "const dernierCycle = flow.get('dernier_cycle') || {};\n"
        "const ANTI_REBOND_MS = 30 * 60 * 1000;\n"
        "const ouverte = etats[m.zone] === true;\n"
        "if (m.potentiel_kpa <= cfg.seuil_sec && !ouverte) {\n"
        "  if (Date.now() - (dernierCycle[m.zone] || 0) < ANTI_REBOND_MS) return null;\n"
        "  dernierCycle[m.zone] = Date.now();\n"
        "  flow.set('dernier_cycle', dernierCycle);\n"
        "  msg.zone = m.zone; msg.commande = 'open'; msg.volume_ml = cfg.volume_max_l * 1000;\n"
        "  node.warn(`[AUTO] ${m.zone}: ${m.potentiel_kpa} kPa <= ${cfg.seuil_sec} -> OUVERTURE`);\n"
        "  return msg;\n"
        "}\n"
        "if (m.potentiel_kpa >= cfg.seuil_humide && ouverte) {\n"
        "  msg.zone = m.zone; msg.commande = 'close';\n"
        "  node.warn(`[AUTO] ${m.zone}: ${m.potentiel_kpa} kPa >= ${cfg.seuil_humide} -> FERMETURE`);\n"
        "  return msg;\n"
        "}\n"
        "return null;\n"),
     "outputs": 1, "noerr": 0, "x": 590, "y": 160, "wires": [["irr_fn_downlink"]]},

    # ================= COMMANDE MANUELLE =================
    {"id": "irr_btn_open", "type": "ui_button", "z": TAB, "name": "OUVRIR",
     "group": "irr_grp_cmd", "order": 2, "width": 0, "height": 0, "passthru": False,
     "label": "OUVRIR la vanne", "tooltip": "", "color": "", "bgcolor": "#00b500", "icon": "play_arrow",
     "payload": "open", "payloadType": "str", "topic": "commande", "topicType": "str",
     "x": 120, "y": 460, "wires": [["irr_fn_manuel"]]},
    {"id": "irr_btn_close", "type": "ui_button", "z": TAB, "name": "FERMER",
     "group": "irr_grp_cmd", "order": 3, "width": 0, "height": 0, "passthru": False,
     "label": "FERMER la vanne", "tooltip": "", "color": "", "bgcolor": "#ca3838", "icon": "stop",
     "payload": "close", "payloadType": "str", "topic": "commande", "topicType": "str",
     "x": 120, "y": 500, "wires": [["irr_fn_manuel"]]},
    {"id": "irr_dd_zone", "type": "ui_dropdown", "z": TAB, "name": "Zone",
     "label": "Zone", "tooltip": "", "place": "Choisir la zone", "group": "irr_grp_cmd",
     "order": 1, "width": 0, "height": 0, "passthru": True, "multiple": False,
     "options": [{"label": "Zone 1", "value": "zone1", "type": "str"},
                 {"label": "Zone 2", "value": "zone2", "type": "str"},
                 {"label": "Zone 3", "value": "zone3", "type": "str"}],
     "payload": "", "topic": "zone", "topicType": "str",
     "x": 110, "y": 420, "wires": [["irr_fn_set_zone"]]},
    {"id": "irr_fn_set_zone", "type": "function", "z": TAB, "name": "Stocke zone",
     "func": "flow.set('zone_selectionnee', msg.payload); return null;",
     "outputs": 1, "noerr": 0, "x": 300, "y": 420, "wires": [[]]},

    {"id": "irr_fn_manuel", "type": "function", "z": TAB, "name": "Commande manuelle",
     "func": (
        "const zone = flow.get('zone_selectionnee');\n"
        "if (!zone) { node.error('Choisir une zone dans le menu déroulant'); return null; }\n"
        "const cfg = flow.get('config') || { volume_max_l: 10 };\n"
        "msg.zone = zone;\n"
        "msg.commande = msg.payload;  // 'open' ou 'close'\n"
        "if (msg.commande === 'open') msg.volume_ml = cfg.volume_max_l * 1000;\n"
        "return msg;\n"),
     "outputs": 1, "noerr": 0, "x": 330, "y": 480, "wires": [["irr_fn_downlink"]]},

    # ================= DOWNLINK TTN =================
    {"id": "irr_fn_downlink", "type": "function", "z": TAB, "name": "Construit downlink TTN",
     "func": (
        "// Mapping zone -> device TTN de la vanne (adapter à vos device IDs)\n"
        "const VANNES = { zone1: 'vanne-zone1', zone2: 'vanne-zone2', zone3: 'vanne-zone3' };\n"
        "const APP_ID = env.get('TTN_APP_ID') || 'MON-APP-TTN';\n"
        "const dev = VANNES[msg.zone];\n"
        "if (!dev) { node.error('Zone inconnue: ' + msg.zone); return null; }\n"
        "let bytes;\n"
        "if (msg.commande === 'close') bytes = [0x00];\n"
        "else if (msg.volume_ml) { const v = Math.round(msg.volume_ml / 100); bytes = [0x02, (v >> 8) & 0xff, v & 0xff]; }\n"
        "else bytes = [0x01];\n"
        "msg.topic = `v3/${APP_ID}@ttn/devices/${dev}/down/push`;\n"
        "msg.payload = JSON.stringify({ downlinks: [{ f_port: 1, frm_payload: Buffer.from(bytes).toString('base64'), priority: 'NORMAL' }] });\n"
        "const etats = flow.get('etats_vannes') || {};\n"
        "etats[msg.zone] = (msg.commande !== 'close');\n"
        "flow.set('etats_vannes', etats);\n"
        "return msg;\n"),
     "outputs": 1, "noerr": 0, "x": 620, "y": 480, "wires": [["irr_mqtt_out_down", "irr_dbg_down"]]},
    {"id": "irr_mqtt_out_down", "type": "mqtt out", "z": TAB, "name": "TTN downlink",
     "topic": "", "qos": "0", "retain": "", "respTopic": "", "contentType": "",
     "userProps": "", "correl": "", "expiry": "", "broker": "irr_mqtt_broker",
     "x": 860, "y": 460, "wires": []},
    {"id": "irr_dbg_down", "type": "debug", "z": TAB, "name": "debug downlink", "active": True,
     "tosidebar": True, "console": False, "tostatus": False, "complete": "true", "targetType": "full",
     "x": 860, "y": 520, "wires": []},

    # ================= ETAT VANNE / DEBIT =================
    {"id": "irr_fn_vanne_status", "type": "function", "z": TAB, "name": "État vanne + débit",
     "func": (
        "const d = msg.decoded;\n"
        "const zone = msg.device_id.replace(/^vanne-?/, '') || 'zone1';\n"
        "const etats = flow.get('etats_vannes') || {};\n"
        "etats[zone] = d.valve_open === true;\n"
        "flow.set('etats_vannes', etats);\n"
        "msg.payload = { zone, valve_open: d.valve_open, cycle_volume_ml: d.cycle_volume_ml, total_volume_l: d.total_volume_l };\n"
        "// Alerte : vanne ouverte mais aucun débit\n"
        "if (d.valve_open && d.cycle_volume_ml === 0) node.warn(`[ALERTE] ${zone}: vanne ouverte sans débit !`);\n"
        "return msg;\n"),
     "outputs": 1, "noerr": 0, "x": 570, "y": 200,
     "wires": [["irr_txt_etat", "irr_fn_influx_irrig"]]},
    {"id": "irr_txt_etat", "type": "ui_text", "z": TAB, "name": "État vanne",
     "group": "irr_grp_etat", "order": 1, "width": 0, "height": 0,
     "label": "Dernier état", "format": "{{msg.payload.zone}} : {{msg.payload.valve_open ? 'OUVERTE' : 'fermée'}} — {{msg.payload.cycle_volume_ml}} mL (total {{msg.payload.total_volume_l}} L)",
     "layout": "col-center", "x": 800, "y": 180, "wires": []},

    # ================= INFLUXDB =================
    {"id": "irr_fn_influx_soil", "type": "function", "z": TAB, "name": "LP soil -> Influx",
     "func": (
        "const m = msg.payload;\n"
        "msg.url = env.get('INFLUX_URL') + '/api/v2/write?org=' + encodeURIComponent(env.get('INFLUX_ORG')) + '&bucket=' + encodeURIComponent(env.get('INFLUX_BUCKET')) + '&precision=ms';\n"
        "msg.method = 'POST';\n"
        "msg.headers = { 'Authorization': 'Token ' + env.get('INFLUX_TOKEN'), 'Content-Type': 'text/plain' };\n"
        "let lp = `soil,zone=${m.zone} matric_potential_kpa=${m.potentiel_kpa}`;\n"
        "if (Number.isFinite(m.temp_c)) lp += `,soil_temp_c=${m.temp_c}`;\n"
        "if (Number.isFinite(m.batterie_v)) lp += `,battery_v=${m.batterie_v}`;\n"
        "msg.payload = lp + ' ' + m.ts;\n"
        "return msg;\n"),
     "outputs": 1, "noerr": 0, "x": 800, "y": 120, "wires": [["irr_http_influx"]]},
    {"id": "irr_fn_influx_irrig", "type": "function", "z": TAB, "name": "LP irrigation -> Influx",
     "func": (
        "const m = msg.payload;\n"
        "msg.url = env.get('INFLUX_URL') + '/api/v2/write?org=' + encodeURIComponent(env.get('INFLUX_ORG')) + '&bucket=' + encodeURIComponent(env.get('INFLUX_BUCKET')) + '&precision=ms';\n"
        "msg.method = 'POST';\n"
        "msg.headers = { 'Authorization': 'Token ' + env.get('INFLUX_TOKEN'), 'Content-Type': 'text/plain' };\n"
        "msg.payload = `irrigation,zone=${m.zone} valve_open=${m.valve_open ? 1 : 0},cycle_volume_ml=${m.cycle_volume_ml || 0},total_volume_l=${m.total_volume_l || 0} ` + Date.now();\n"
        "return msg;\n"),
     "outputs": 1, "noerr": 0, "x": 810, "y": 240, "wires": [["irr_http_influx"]]},
    {"id": "irr_http_influx", "type": "http request", "z": TAB, "name": "POST InfluxDB",
     "method": "use", "ret": "txt", "paytoqs": "ignore", "url": "", "persist": False,
     "proxy": "", "authType": "", "x": 1040, "y": 180, "wires": [[]]},
]

flows.extend(new_nodes)

with io.open(FLOWS, "w", encoding="utf-8") as f:
    json.dump(flows, f, indent=2, ensure_ascii=False)

print(f"OK: flux 'IoT Irrigation Piloté' ajouté ({len(new_nodes)} noeuds), total {len(flows)} noeuds")
