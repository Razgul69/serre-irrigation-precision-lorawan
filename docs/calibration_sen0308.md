# Protocole de calibration — DFRobot Gravity SEN0308 (sonde capacitive étanche V2.0)

Sonde : [DFRobot SEN0308](https://www.dfrobot.com/product-2054.html) — [wiki](https://wiki.dfrobot.com/sen0308/)

| Caractéristique | Valeur |
|---|---|
| Alimentation | 3,3 – 5,5 V DC |
| Sortie | analogique 0 – 3 V (**décroît** quand l'humidité augmente) |
| Câble | rouge = VCC, noir = GND, **jaune = signal** |
| Lecture dans l'air (5 V, ADC 10 bits) | 500 – 660 (≈ 2,4 – 3,2 V) — varie d'une sonde à l'autre |
| Lecture dans l'eau | ≈ 0 |
| Profondeur d'insertion | entre « Recommend Depth » et « Warning Line » gravées sur la sonde |

La sonde donne un **indice relatif d'humidité**, pas une teneur en eau absolue : la réponse dépend du substrat,
du tassement, de la profondeur d'insertion et de la tension d'alimentation. D'où ce protocole en trois niveaux :

| Niveau | Résultat | Durée | Quand |
|---|---|---|---|
| **1 — Air / eau** | indice 0 – 100 % | 10 min / sonde | Obligatoire, à chaque sonde, à chaque changement d'alimentation |
| **2 — Gravimétrique** | teneur en eau volumique θ (% vol.) | 1 à 3 jours | Si l'on veut des % d'eau réels ou comparer des substrats |
| **3 — Co-localisation TEROS** | relation indice ↔ kPa pour le substrat | en continu | Pour fixer les seuils d'irrigation sur l'indice SEN0308 |

---

## Règles communes

1. **Même chaîne de mesure qu'en service** : la tension de sortie dépend de l'alimentation. Une sonde calibrée sur
   le CR1000 (5 V) ne garde pas ses constantes sur un Nano ESP32 (3,3 V). Calibrer avec le datalogger/MCU, le câble
   et l'alimentation définitifs.
2. **Une calibration par sonde** : noter le numéro de série ou étiqueter chaque sonde (étiquettes fournies).
3. **Attendre la stabilisation** : alimenter ≥ 2 min avant la première lecture, puis moyenner ≥ 30 s de lectures
   (le firmware et le programme CR1000 fournis font déjà la médiane / moyenne).
4. **Profondeur constante** : repérer sur la sonde la ligne d'insertion (marqueur indélébile) et l'utiliser pour la
   calibration ET sur le terrain.
5. **Température** : calibrer à la température moyenne d'usage (serre ≈ 20 – 30 °C). Un écart de 10 °C peut
   décaler la lecture de quelques %. Noter la température du substrat (celle de la TEROS fait l'affaire).

## Matériel

- Sonde(s) SEN0308 + chaîne d'acquisition définitive (CR1000 **ou** Nano ESP32 + PC)
- Récipient d'eau du robinet (hauteur ≥ profondeur d'insertion), chiffon
- Pour le niveau 2 : balance Ohaus DP15/M du projet (`balance/`), pots de volume connu, étuve (105 °C sol minéral ;
  70 °C substrat organique/tourbe), sac plastique
- Fiche de relevé : copier le tableau en fin de document ou utiliser `tools/calib_sen0308.py` (Nano ESP32)

---

## Niveau 1 — Calibration air / eau (indice relatif)

| Étape | Action | Relevé |
|---|---|---|
| 1 | Brancher la sonde, alimenter 2 min. | — |
| 2 | Sonde **sèche, tenue en l'air** à ≥ 20 cm de tout objet, à la main par le haut du corps. Moyenner 30 s. | `AIR_MV` (mV) |
| 3 | Essuyer. Plonger dans l'eau **jusqu'à la ligne d'insertion**, sans toucher les parois. Moyenner 30 s. | `WATER_MV` (mV) |
| 4 | Sortir, essuyer, attendre 1 min, refaire l'étape 2. Écart < 2 % de `AIR_MV` → OK, sinon recommencer. | `AIR_MV` bis |
| 5 | Reporter les constantes (voir § Où saisir les constantes). | — |

Indice d'humidité :

$$
\text{Indice}_{\%} = 100 \times \frac{AIR\_MV - mV}{AIR\_MV - WATER\_MV}
\quad\text{(borné à } 0 \ldots 100\text{)}
$$

Ordres de grandeur attendus (5 V) : `AIR_MV` ≈ 2 400 – 3 200 mV, `WATER_MV` ≈ 0 – 100 mV. Sous 3,3 V les valeurs sont
plus basses ; c'est normal, c'est pour cela qu'on calibre sur la chaîne définitive.

Interprétation DFRobot par tiers : indice 0 – 33 % « sec », 33 – 66 % « humide », 66 – 100 % « très humide ».

---

## Niveau 2 — Calibration gravimétrique (θ en % volumique)

Objectif : obtenir θ = f(mV) pour **votre substrat**. Cinq points suffisent (sec → saturé).

1. **Préparer** un pot de volume intérieur connu $V$ (L) rempli de substrat au tassement de culture, sonde insérée
   à la ligne repère. Peser l'ensemble vide (pot + sonde) : $m_0$.
2. **Saturer** le substrat (arroser, laisser drainer 30 min, boucher le drainage). Peser : $m_1$. Lire la sonde
   (moyenne 30 s) : $mV_1$.
3. **Laisser sécher** (serre, ventilateur) et répéter peser + lire la sonde à intervalles : viser 5 à 7 couples
   $(m_i, mV_i)$ répartis entre saturé et sec. Entre deux relevés ne pas déplacer la sonde.
4. **Point sec** : retirer la sonde, passer le substrat à l'étuve jusqu'à masse constante (24 – 48 h). Peser pot +
   substrat sec : $m_{sec}$ (remettre le pot seul dans la pesée si la sonde est retirée : adapter $m_0$).
5. **Calculer** pour chaque point :

$$
\theta_i\,[\%] = 100 \times \frac{m_i - m_{sec}}{\rho_w \, V}
\qquad (\rho_w = 1\ \text{kg/L})
$$

6. **Ajuster** une droite $\theta = a \cdot mV + b$ (ou un polynôme de degré 2 si la droite s'écarte > 3 %) —
   `tools/calib_sen0308.py --fit` le fait à partir du CSV. Critères : $R^2 \ge 0{,}95$, résidus < 3 % vol.

Astuce : la balance du projet remonte déjà le poids dans InfluxDB (`collect_balance.py`) ; si la sonde est sur le
Nano ESP32 + `calib_sen0308.py`, les deux séries sont horodatées et se croisent directement dans Grafana.

---

## Niveau 3 — Co-localisation avec la TEROS (seuils d'irrigation)

La TEROS 21/22 mesure le potentiel matriciel (kPa), grandeur agronomique sur laquelle sont définis `SEUIL_SEC`
(−40 kPa) et `SEUIL_HUMIDE` (−10 kPa). Pour piloter aussi sur la SEN0308 :

1. Installer SEN0308 et TEROS **côte à côte** (5 – 10 cm, même profondeur) dans un pot représentatif.
2. Laisser tourner 1 à 2 cycles complets d'irrigation/dessèchement (le CR1000 enregistre les deux toutes les 15 min).
3. Tracer indice SEN0308 (ou θ) en fonction de kPa (Grafana ou Excel) : la courbe de rétention du substrat.
4. Lire l'indice correspondant à −40 kPa et −10 kPa → seuils `SEN_SEC` / `SEN_HUMIDE` à saisir dans Node-RED.

Refaire ce niveau si l'on change de substrat ou de tassement (rempotage).

---

## Validation et suivi

- **Répétabilité d'insertion** : retirer/réinsérer 3 fois dans le même pot ; coefficient de variation < 5 %.
- **Dérive** : contrôler `AIR_MV` tous les 3 mois (sonde sortie, séchée) ; si écart > 5 %, recalibrer.
- **Encrassement** : rincer la sonde à l'eau claire, ne pas gratter la surface.
- Conserver la fiche de relevé dans `docs/` (une par sonde) et dater les constantes dans le code.

## Où saisir les constantes

| Chaîne | Fichier | Constantes |
|---|---|---|
| Campbell CR1000 | `campbell/teros22_sen0308_cr1000.CR1` | `SEN_AIR_MV`, `SEN_WATER_MV`, (`SEN_A`, `SEN_B` si niveau 2) |
| Arduino Nano ESP32 | `firmware/esp32_nano_sen0308/src/config.h` | `AIR_MV`, `WATER_MV`, (`VWC_A`, `VWC_B`) |
| Node-RED (seuils) | flux « IoT Irrigation Piloté » | `SEN_SEC`, `SEN_HUMIDE` (niveau 3) |

## Fiche de relevé (à copier par sonde)

| Sonde n° | Date | Chaîne / alim. | T° (°C) | AIR_MV | WATER_MV | AIR_MV bis | Opérateur | Remarques |
|---|---|---|---|---|---|---|---|---|
| | | CR1000 5 V / Nano 3,3 V | | | | | | |

Niveau 2 (gravimétrique) — substrat : ______ , $V$ = ____ L, $m_0$ = ____ g, $m_{sec}$ = ____ g

| Point | Date / heure | $m_i$ (g) | $mV_i$ | $\theta_i$ (%) |
|---|---|---|---|---|
| 1 (saturé) | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 (sec) | | | | |
