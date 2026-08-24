# Dashboard Grafana

## Contenu versionné (installation locale D:\Grafana)

- `dashboards/sonde_kpa.json` et `dashboards/sonde_temperature.json` : dashboards en production (bucket `sondes`, org `ird`).
- `provisioning/datasources/influxdb.yaml` : datasource InfluxDB (Flux) — remplacer `${INFLUX_TOKEN}` par votre token.
- `provisioning/dashboards/dashboards.yaml` : chargement auto des dashboards depuis `D:\Grafana\dashboards`.

Panels recommandés (datasource InfluxDB, bucket `irrigation`) :

1. **Potentiel matriciel par zone** (time series, kPa) — seuils sec/humide en lignes de référence
2. **Température du sol** (time series, °C)
3. **État des vannes** (state timeline, ouvert/fermé)
4. **Volume d'eau par cycle** (bar chart, mL)
5. **Volume cumulé journalier par zone** (stat + bar chart, L)
6. **Batteries des Dragino** (gauge, V)
7. **Alertes** : potentiel < -80 kPa, vanne ouverte sans débit

Exemple de requête Flux (potentiel matriciel) :

```flux
from(bucket: "irrigation")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "soil" and r._field == "matric_potential_kpa")
  |> aggregateWindow(every: v.windowPeriod, fn: mean)
```
