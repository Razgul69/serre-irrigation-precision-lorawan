# TEROS 22 (+ DFRobot SEN0308) sur Campbell CR1000

Deux programmes :

- `teros22_cr1000.CR1` : TEROS 22 seule.
- `teros22_sen0308_cr1000.CR1` : TEROS 22 + sonde capacitive DFRobot SEN0308 sur le meme datalogger (table `MesuresSol`), avec une table `CalibSEN0308` activable pour la calibration.
- `teros22_sen0308_cr800.CR8` : meme programme pour **CR800** (cablage identique : TEROS sur C3, SEN0308 sur 5V / G / 1H). Copie deposee dans `D:\Mes Programmes\SCWin\sys\teros sen0308 v1.CR8`.

La balance est acquise separement par l'ordinateur.

## SEN0308 (sonde capacitive analogique)

- rouge -> borne `5V` du CR1000 (la sonde accepte 3,3 - 5,5 V ; **ne pas** brancher sur 12V) ;
- noir -> `G` ;
- jaune (signal 0 - 3 V) -> `1H` (single-ended 1, `VoltSE` plage mV5000).

Calibration : suivre `docs/calibration_sen0308.md`. Mettre `CalibOn = True` dans la table `Public` : la table `CalibSEN0308` enregistre alors moyenne et ecart-type de `SEN_mV` toutes les 30 s (air, eau, puis chaque point gravimetrique). Reporter `SEN_AIR_MV` / `SEN_WATER_MV` (et `SEN_A` / `SEN_B` avec `SEN_USE_VWC = True` apres calibration gravimetrique) en tete du programme, recompiler et renvoyer.

Sorties : `SEN_mV` (brut), `SEN_Index_pct` (indice relatif 0-100 %), `SEN_VWC_pct` (teneur en eau volumique, NAN tant que `SEN_USE_VWC = False`).

## Cablage

Verifier le code couleur sur l'etiquette ou la notice de la sonde avant raccordement :

- alimentation positive de la TEROS 22 vers `12V` ;
- masse vers `G` ;
- donnees SDI-12 vers `C3`.

Le programme suppose l'adresse SDI-12 usine `0`. Modifier `SDI_ADDR` si la sonde utilise une autre adresse.

## Acquisition

- mesure TEROS 22 : toutes les 60 secondes ;
- enregistrement dans `MesuresTEROS22` : toutes les 15 minutes ;
- champs exportes : batterie CR1000, temperature du panneau, potentiel matriciel et temperature du sol.

Compiler d'abord le fichier dans CRBasic Editor pour la cible **CR1000**, puis l'envoyer avec LoggerNet ou PC400. Avant l'essai, controler dans la table `Public` que `WaterPot_kPa` et `SoilTemp_C` changent et ne valent pas `NAN`.

Pour l'export manuel, recuperer la table `MesuresTEROS22` au format TOA5/CSV en conservant l'horodatage du datalogger.
## Calibration SEN0308 seule

`calib_sen0308_cr1000.CR1` : programme de banc (sonde seule, scan 1 s). Dans Public : `SEN_mV_1min` (moyenne 60 s a relever), `SEN_Std` (attendre < 10 mV), `Point` (numero de point saisi a la main, stocke dans la table). Table `CalibSEN0308` toutes les 30 s. Copie : `D:\Mes Programmes\SCWin\sys\calib sen0308 cr1000.CR1`.
