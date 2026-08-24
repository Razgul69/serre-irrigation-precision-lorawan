# Orchestration Node-RED

## Flux disponibles

- `flows_production.json` : **flux réellement en production** (export de `C:\Users\VIAL\.node-red\flows.json`) — uplink TEROS21 (app TTN `sondehumidite`, device `humidity-probe`) → InfluxDB local (bucket `sondes`, measurement `sonde_matricielle`) + boutons Ouverture/Fermeture de l'électrovanne (downlink TTN) sur le dashboard Node-RED. Les credentials (clé API TTN, token InfluxDB) ne sont pas versionnés : les ressaisir après import.
- `flow_iot_irrigation_pilote.json` : flux pilote cible multi-zones avec seuils automatiques.

## Connexion TTN (MQTT)

- Broker : `eu1.cloud.thethings.network:8883` (TLS)
- Username : `<app-id>@ttn` — Password : clé API TTN
- Uplinks : `v3/<app-id>@ttn/devices/+/up`
- Downlink : publier sur `v3/<app-id>@ttn/devices/<device-id>/down/push`

## Logique d'irrigation (par zone)

```
Uplink TEROS21 (zone N)
  └─> stocker dans InfluxDB (measurement: soil, tags: zone)
  └─> évaluer les seuils :
        potentiel < SEUIL_SEC  (ex: -40 kPa)  ET vanne fermée
            └─> downlink {"command":"open","volume_ml":5000} vers vanne zone N
        potentiel > SEUIL_HUMIDE (ex: -10 kPa) ET vanne ouverte
            └─> downlink {"command":"close"} vers vanne zone N

Uplink contrôleur vanne (zone N)
  └─> stocker dans InfluxDB (measurement: irrigation, tags: zone)
      champs : valve_open, cycle_volume_ml, total_volume_l
```

## Configuration des seuils

Stocker les seuils par zone dans un nœud `change`/`context` ou un fichier JSON :

```json
{
  "zone1": { "seuil_sec": -40, "seuil_humide": -10, "volume_max_ml": 10000 },
  "zone2": { "seuil_sec": -35, "seuil_humide": -8,  "volume_max_ml": 8000 }
}
```

## Garde-fous côté serveur

- Anti-rebond : minimum 30 min entre deux cycles d'une même zone
- Alerte (email/Telegram) si le débitmètre mesure 0 L alors que la vanne est ouverte (vanne HS ou fuite réseau)
- Alerte si potentiel < -80 kPa (stress hydrique sévère)
