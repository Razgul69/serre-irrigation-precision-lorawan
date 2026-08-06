# -*- coding: utf-8 -*-
"""Genere le document Word du projet Irrigation de Precision LoRaWAN."""
from docx import Document
from docx.shared import Pt, RGBColor, Cm

doc = Document()

def h(text, level=1):
    doc.add_heading(text, level=level)

def p(text, bold=False):
    par = doc.add_paragraph()
    run = par.add_run(text)
    run.bold = bold
    return par

def table(headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    for i, htxt in enumerate(headers):
        t.rows[0].cells[i].text = htxt
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
    doc.add_paragraph()

# Titre
title = doc.add_heading("Irrigation de Précision LoRaWAN — Serre", level=0)
p("Système d'irrigation piloté par le potentiel matriciel du sol, inspiré du projet "
  "Makerfabs IoT Irrigation System (github.com/Makerfabs/Project_IoT-Irrigation-System).")
p("Dépôt GitHub : https://github.com/Razgul69/serre-irrigation-precision-lorawan", bold=True)

h("1. Architecture générale")
p("Chaîne de mesure : sondes TEROS 21 (METER) → convertisseurs Dragino SDI-12 → LoRaWAN → "
  "passerelle LoRa dans la serre → The Things Network (TTN) → serveur virtuel.")
p("Chaîne de commande : Node-RED (orchestrateur) évalue les seuils d'irrigation et envoie des "
  "downlinks LoRaWAN vers des ESP32 qui pilotent une électrovanne par sonde (irrigation zonale). "
  "Un débitmètre à impulsions sur chaque ESP32 mesure l'apport d'eau exact.")
p("Stockage et visualisation : InfluxDB + Grafana (tensiométrie, volumes, états des vannes, alertes).")

h("2. Matériel")
table(["Élément", "Référence", "Rôle"], [
    ["Sonde tensiométrique", "METER TEROS 21", "Potentiel matriciel + température sol (SDI-12)"],
    ["Convertisseur", "Dragino SDI-12-LB", "SDI-12 vers LoRaWAN, alimenté batterie"],
    ["Passerelle", "Passerelle LoRaWAN 868 MHz", "Uplink/downlink vers TTN"],
    ["Contrôleur vanne", "ESP32 + RFM95/SX1276", "Pilotage électrovanne + comptage débit"],
    ["Électrovanne", "12/24 V (1 par sonde/zone)", "Irrigation zonale de précision"],
    ["Débitmètre", "À impulsions (ex. YF-S201)", "Mesure de l'apport d'eau"],
    ["Serveur", "VPS Docker", "Node-RED + InfluxDB + Grafana"],
])

h("3. Logique d'irrigation")
table(["Paramètre", "Valeur par défaut", "Description"], [
    ["SEUIL_SEC", "-40 kPa", "En dessous : démarrer l'irrigation"],
    ["SEUIL_HUMIDE", "-10 kPa", "Au-dessus : arrêter l'irrigation"],
    ["VOLUME_MAX", "10 L", "Sécurité : volume max par cycle"],
    ["DUREE_MAX", "15 min", "Sécurité : durée max d'ouverture"],
])
p("Sécurités embarquées dans l'ESP32 (autonomes même en cas de perte réseau) : "
  "fermeture automatique sur durée max ou volume max atteint.")
p("Garde-fous côté serveur : anti-rebond 30 min entre cycles, alerte si vanne ouverte sans débit "
  "(vanne HS/fuite), alerte stress hydrique si potentiel < -80 kPa.")

h("4. Protocole LoRaWAN")
p("Uplink contrôleur vanne (port 2) : état vanne (1 o), volume du cycle en mL (4 o), "
  "volume total en L x10 (2 o), uptime en minutes (2 o).")
p("Downlink (port 1) : 0x00 = fermer ; 0x01 = ouvrir ; 0x02 + volume/100 mL (2 o) = "
  "ouvrir avec limite de volume.")
p("Uplink Dragino/TEROS21 : batterie (mV) + réponse SDI-12 ASCII "
  "(potentiel matriciel kPa + température °C), décodée par le payload formatter TTN.")

h("5. Structure du dépôt")
table(["Dossier", "Contenu"], [
    ["firmware/esp32_valve_controller/", "Firmware PlatformIO (LMIC, vanne, débitmètre, sécurités)"],
    ["ttn/", "Décodeurs de payload TTN (TEROS21 et contrôleur vanne)"],
    ["server/docker-compose.yml", "Stack Node-RED + InfluxDB 2.x + Grafana"],
    ["server/nodered/", "Documentation du flow d'orchestration et des seuils par zone"],
    ["grafana/", "Panels recommandés et requêtes Flux"],
    ["docs/images/", "Photos du montage (serre, sondes, vannes, passerelle)"],
])

h("6. Mise en route")
for step in [
    "1. TTN : créer une application, enregistrer les Dragino et les ESP32 en OTAA, coller les décodeurs.",
    "2. Serveur : docker compose up -d, configurer l'intégration MQTT TTN dans Node-RED.",
    "3. Firmware : renseigner les clés OTAA dans config.h, compiler avec PlatformIO, flasher.",
    "4. Grafana : créer la datasource InfluxDB et les panels (voir grafana/README.md).",
    "5. Calibrer les seuils par zone selon la culture et le substrat.",
]:
    p(step)

h("7. État d'avancement (06/08/2026)")
table(["Étape", "État"], [
    ["Firmware ESP32 vanne + débitmètre", "FAIT (à flasher/tester)"],
    ["Décodeurs TTN (TEROS21, vanne)", "FAIT"],
    ["Stack Docker Node-RED/InfluxDB/Grafana", "OPÉRATIONNELLE en local (ports 11880/18086/13000)"],
    ["Flux Node-RED « IoT Irrigation Piloté »", "DÉPLOYÉ : dashboard /ui avec jauge kPa, seuils réglables, mode auto, boutons OUVRIR/FERMER par zone, écriture InfluxDB, downlinks TTN"],
    ["Export du flux (importable)", "server/nodered/flow_iot_irrigation_pilote.json"],
    ["Application TTN", "À CRÉER (identifiants MQTT à renseigner dans Node-RED)"],
    ["Enregistrement devices (Dragino, ESP32)", "À FAIRE"],
    ["Installation terrain (sondes, vannes, passerelle)", "À FAIRE"],
    ["Photos du montage", "À AJOUTER dans docs/images/"],
])

doc.save(r"D:\Projet_Irrigation_LoRaWAN\Projet_Irrigation_Precision_LoRaWAN.docx")
print("OK: D:\\Projet_Irrigation_LoRaWAN\\Projet_Irrigation_Precision_LoRaWAN.docx")
