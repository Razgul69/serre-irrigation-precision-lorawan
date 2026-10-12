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

1. **Préparer** un pot de volume connu $V$ (L — nominal, pichet gradué ou calcul) rempli de substrat au tassement de culture, sonde insérée
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

### Mini-protocole pas à pas sur Campbell (CR800 / CR1000) → `SEN_USE_VWC = True`

Pré-requis : niveau 1 fait, `SEN_AIR_MV` / `SEN_WATER_MV` déjà dans le programme, programme chargé, sonde alimentée
en 5 V par le datalogger. Durée : 1 à 2 semaines calendaires (séchage), ~15 min de manipulation par point.

**J0 — Préparation**

| # | Action | À noter |
|---|---|---|
| 1 | Peser le pot vide : $m_{pot}$. Volume $V$ (mL) : volume nominal du pot, pichet gradué, ou calcul à partir des dimensions. | $m_{pot}$, $V$ |
| 2 | Remplir de substrat au tassement de culture (même geste qu'un rempotage), arroser légèrement pour qu'il tienne. | substrat, date |
| 3 | Insérer la SEN0308 verticalement jusqu'à la **ligne repère**, au centre du pot. Si possible la TEROS à 5–10 cm. | — |
| 4 | Fixer le câble de la sonde à un support (potence, pince) avec une boucle lâche vers le pot : le câble doit peser **de la même façon à chaque pesée**. Marquer la position du pot sur la balance. | — |
| 5 | Saturer : arroser jusqu'à ruissellement, laisser drainer 30 min (trou ouvert), puis boucher le trou. | — |

**Chaque point de mesure (point 1 = saturé, puis tous les 1–3 jours selon le séchage ; viser 5 à 7 points)**

| # | Action | À noter |
|---|---|---|
| a | Dans LoggerNet/PC400 → table `Public` : mettre `CalibOn = True`. Attendre **5 min** sans toucher le pot. | heure |
| b | Collecter la table `CalibSEN0308` : prendre la **moyenne des 10 dernières lignes** de `SEN_mV_Avg` (= 5 min). Vérifier `SEN_mV_Std` < 10 mV, sinon attendre encore. Noter aussi `WaterPot_kPa` et `SoilTemp_C`. | $mV_i$, kPa, T° |
| c | Remettre `CalibOn = False`. | — |
| d | Poser le pot sur la balance (position marquée, câble dans sa boucle), lire le poids **stable** (`S S` sur le collecteur) : $m_i$. | $m_i$ |
| e | Reposer le pot au même endroit. Entre deux points : laisser sécher à l'air (serre, ventilateur) ; **ne jamais** retirer ni enfoncer la sonde. | — |

Répartir les points : saturé → 1–2 jours → 3–4 jours → … jusqu'à ce que la plante flétrirait (indice ≈ 10–20 %).
Si le séchage est trop lent, ventiler ; s'il est trop rapide (point sautés), couvrir partiellement.

**Dernier point et point sec**

| # | Action | À noter |
|---|---|---|
| 6 | Faire un dernier point normal (a → d). Puis, sans attendre, peser le pot **avec** sonde ($m_{avec}$) et, après avoir retiré la sonde, **sans** sonde ($m_{sans}$). $\Delta_{sonde} = m_{avec} - m_{sans}$ = masse apparente de la sonde + câble, à soustraire de tous les $m_i$. | $\Delta_{sonde}$ |
| 7 | Étuve : 105 °C (substrat minéral) ou 70 °C (tourbe, fibre de coco, terreau) jusqu'à masse constante : peser à 24 h et 48 h, écart < 0,1 % → stop. Peser pot + substrat sec : $m_{sec}$. | $m_{sec}$ |

**Calcul** (une ligne par point, g et mL) :

$$
\theta_i\,[\%] = 100 \times \frac{(m_i - \Delta_{sonde}) - m_{sec}}{V}
$$

Contrôle de vraisemblance : point saturé ≈ 40–60 % pour un terreau/tourbe, 30–45 % pour un substrat minéral ;
dernier point ≈ 5–15 %. Une valeur > 70 % ou < 0 % trahit une erreur de $V$, de $m_{sec}$ ou de câble.

**Ajustement et saisie dans le programme**

1. Créer `points_<sonde>_<substrat>.csv` avec l'en-tête `mv,theta_pct` et une ligne par point.
2. `python tools/calib_sen0308.py --fit points_<sonde>_<substrat>.csv` → affiche `SEN_A`, `SEN_B`, $R^2$ et les
   résidus. Accepter si $R^2 \ge 0{,}95$ et résidu max < 3 % vol ; sinon essayer `--deg 2` (voir remarque) ou
   refaire les points aberrants.
3. Dans `teros22_sen0308_cr800.CR8` (ou `_cr1000.CR1`) :
   ```
   Const SEN_USE_VWC  = True
   Const SEN_A = -0.018737     'valeur affichee par --fit
   Const SEN_B = 50.824
   ```
   Dater en commentaire (sonde n°, substrat, date). Compiler, envoyer.
4. Vérifier dans `Public` que `SEN_VWC_pct` n'est plus `NAN` et tombe dans la plage attendue.
5. **Validation** : un point indépendant (une pesée + lecture) sur un autre pot du même substrat → écart entre θ
   pesé et `SEN_VWC_pct` < 3 % vol. Archiver le CSV et la fiche dans `docs/`.

Remarques :
- La droite n'est valable que pour **ce substrat, ce tassement et cette alimentation 5 V**. Nouveau substrat =
  nouveau niveau 2 ; nouveau datalogger = refaire au moins le niveau 1.
- Si `--deg 2` est nécessaire, remplacer dans le programme la ligne `SEN_VWC_pct = SEN_A * SEN_mV + SEN_B` par
  `SEN_VWC_pct = SEN_A2 * SEN_mV^2 + SEN_A * SEN_mV + SEN_B` et ajouter `Const SEN_A2`.
- `SEN_Index_pct` (niveau 1) reste calculé en parallèle : il sert de garde-fou si la droite dérive.

### Variante « réhumidification » : partir d'un terreau déjà sec et remonter jusqu'à la saturation

À utiliser quand on dispose d'un volume de terreau **séché à l'avance** (≈ volume du pot). On ajoute l'eau par
paliers connus au lieu d'attendre le séchage : la calibration tient en **une journée**. Les points sont obtenus en
mélangeant l'eau au substrat hors du pot puis en re-remplissant le pot à l'identique — c'est ce qui garantit une
humidité homogène (le terreau sec est hydrophobe : versé par-dessus, l'eau ruisselle et le capteur verrait un
gradient).

Attention au vocabulaire : le « 100 % » du niveau 1 est la sonde **dans l'eau** (`SEN_WATER_MV`). Un terreau saturé
donnera un indice intermédiaire (typiquement 60–80 %) : c'est normal, et c'est précisément ce que mesure le niveau 2.

**Matériel** : le terreau sec, pot repère (volume $V$ connu, trait de remplissage marqué), balance, grand sac
plastique ou seau avec couvercle, eau tiède, pichet gradué, CR800 avec `CalibOn`, étuve ou four (facultatif).

**A — Point zéro (terreau sec)**

| # | Action | À noter |
|---|---|---|
| 1 | Peser le pot vide ($m_{pot}$). Volume $V$ (mL) : prendre le volume nominal du pot (ex. 2 L), ou le remplir au pichet gradué, ou le calculer ($\pi r^2 h$ ; conique : $\frac{\pi h}{3}(R^2+Rr+r^2)$). Marquer le trait de remplissage. | $m_{pot}$, $V$ |
| 2 | Humidité résiduelle (recommandé) : prélever 50–100 g de terreau « sec », peser ($m_h$), étuve 70 °C 24 h, repeser ($m_d$). $w_{res} = (m_h - m_d)/m_d$. Un terreau séché à l'air garde 5–15 % d'eau en masse. Sans étuve : $w_{res} = 0{,}10$ par défaut et le noter. | $w_{res}$ |
| 3 | Remplir le pot de terreau sec jusqu'au trait avec le tassement de culture. Peser → masse de substrat $m_s = m_{total} - m_{pot}$. Densité apparente $\rho_b = m_s / V$ (attendu 0,15–0,35 g/mL). | $m_s$, $\rho_b$ |
| 4 | Insérer la SEN0308 jusqu'à la ligne repère, attendre 15 min, `CalibOn = True`, 5 min, moyenne des 10 lignes de `CalibSEN0308` → $mV_0$. `CalibOn = False`. | $mV_0$ |
| 5 | $\theta_0 = 100 \times w_{res} \times \rho_b$ (≈ 1–4 % vol). Retirer la sonde. | $\theta_0$ |

**B — Paliers de réhumidification** (viser 5 paliers de ~10 % vol, puis la saturation)

Masse d'eau par palier : $\Delta W = 0{,}10 \times V$ grammes (ex. pot de 2 000 mL → 200 g d'eau par palier).

| # | Action | À noter |
|---|---|---|
| 6 | Vider **tout** le terreau du pot dans le sac/seau. Ajouter $\Delta W$ g d'eau tiède (peser au pichet, pas au volume), en 3–4 fois en malaxant. Fermer, laisser reposer **30 min**, re-malaxer. | $W_{cumul}$ |
| 7 | Remettre **tout** le terreau dans le pot jusqu'au trait, même geste de tassement (le terreau humide gonfle : tasser légèrement pour revenir au trait ; s'il en reste, peser le reliquat $r$ et le déduire : eau et solide au prorata $r/(m_s+W_{cumul})$). Peser le pot plein → contrôle : $m_{pot} + m_s + W_{cumul}$ à ± 1 % près. | $m_{plein,i}$ |
| 8 | Insérer la sonde jusqu'à la ligne repère, attendre 15 min (température), `CalibOn = True`, 5 min, moyenne → $mV_i$ ; vérifier `SEN_mV_Std` < 10 mV. `CalibOn = False`, retirer la sonde. | $mV_i$ |
| 9 | $\theta_i = 100 \times \dfrac{W_{cumul} + w_{res} \, m_s}{V}$ (le reliquat $r$ éventuel enlevé). Répéter 6 → 9. | $\theta_i$ |

**C — Point saturé (capacité de rétention du pot)**

| # | Action | À noter |
|---|---|---|
| 10 | Après le dernier palier, sonde en place : arroser lentement jusqu'à ce que l'eau affleure en surface, laisser drainer 30 min trou ouvert, boucher. Peser le pot → $W_{sat} = m_{plein} - m_{pot} - m_s$. Lire $mV_{sat}$ (15 min + 5 min `CalibOn`). | $W_{sat}$, $mV_{sat}$ |
| 11 | $\theta_{sat} = 100 \times (W_{sat} + w_{res} m_s)/V$ — attendu 45–70 % pour un terreau. Au-delà de 80 % : vérifier $V$. | $\theta_{sat}$ |

**D — Contrôle d'hystérésis (facultatif mais conseillé, 2–3 jours)**

Laisser ce pot saturé sécher à l'air sans toucher la sonde et faire 2 points « en séchage » (pesée + $mV$, méthode
du mini-protocole précédent). S'ils tombent sur la droite à ± 3 % vol, la calibration vaut dans les deux sens.

**E — Ajustement**

CSV `mv,theta_pct` avec les points 0, paliers, saturé (6–8 lignes) → `python tools/calib_sen0308.py --fit …` →
`SEN_A`, `SEN_B` → `SEN_USE_VWC = True` dans le programme CR800, compiler, envoyer, vérifier `SEN_VWC_pct`.

Points de vigilance :
- Toujours **toute** la masse de terreau dans le pot, jusqu'au trait : c'est ce qui maintient $\rho_b$ constant.
- Même profondeur de sonde à chaque palier (ligne repère) ; insérer d'un seul geste, sans remuer.
- Les 15 min d'attente servent à ce que l'eau tiède revienne à la température ambiante (la sonde y est sensible).
- Travailler à l'ombre, sac fermé entre les étapes : l'évaporation pendant la manipulation doit rester < 1 % de $\Delta W$.

| Palier | $W_{cumul}$ (g) | $m_{plein}$ (g) | $mV$ | `Std` | $\theta$ (%) |
|---|---|---|---|---|---|
| 0 (sec) | 0 | | | | |
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |
| sat | | | | | |

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
