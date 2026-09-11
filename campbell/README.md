# TEROS 22 sur Campbell CR1000

Le programme `teros22_cr1000.CR1` mesure uniquement la TEROS 22. La balance sera acquise separement par l'ordinateur.

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