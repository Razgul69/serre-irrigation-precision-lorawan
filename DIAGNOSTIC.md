# Diagnostic de la balance Ohaus sur macOS

Ce guide sert à déterminer si le problème vient de l’adaptateur USB-C, de la détection du port série, de l’ouverture du port ou de la communication avec la balance.

## 1. Comprendre les indicateurs de l’application

L’application macOS affiche désormais séparément les étapes suivantes :

| Message | Signification |
|---|---|
| **Aucun port USB détecté** | macOS/PySerial ne voit aucun adaptateur série correspondant. |
| **Port USB détecté** | L’adaptateur USB–série est visible, mais la balance n’a pas encore répondu. |
| **Port série ouvert – attente de la balance** | L’application a pu ouvrir le port. Il n’est donc probablement pas occupé par un autre logiciel. |
| **BALANCE CONNECTÉE : réponse reçue** | Des octets ont effectivement été reçus de la balance. Cela ne garantit pas encore que leur format est reconnu comme un poids. |
| **Connexion : échec** | Le port n’a pas pu être ouvert ou une erreur série s’est produite. Le message détaillé apparaît au-dessus. |

Après avoir branché la balance, cliquer sur **Actualiser**, choisir le port si plusieurs ports sont proposés, puis cliquer sur **MARCHE**. Une première réponse peut prendre quelques secondes.

## 2. Vérifier l’adaptateur USB vers USB-C

Le Mac n’ayant que des connecteurs USB-C, la chaîne est probablement :

**Balance → câble/adaptateur USB–série → adaptateur USB-A vers USB-C → Mac**

L’adaptateur USB-A vers USB-C est une cause possible, surtout s’il s’agit d’un hub. Vérifier dans cet ordre :

1. Débrancher puis rebrancher toute la chaîne.
2. Essayer un autre port USB-C du Mac.
3. Si possible, tester sans hub ou station d’accueil.
4. Essayer un autre adaptateur USB-A vers USB-C compatible **données** — certains câbles/adaptateurs ne servent qu’à la charge.
5. Réutiliser exactement le même câble USB–série et la même balance que sur Windows.
6. Dans les réglages de confidentialité/sécurité de macOS, autoriser la connexion du nouvel accessoire si une demande apparaît.

Si l’adaptateur fonctionne sur Windows mais n’apparaît pas sur macOS, son chipset peut nécessiter un pilote macOS compatible. Les chipsets courants sont FTDI, CP210x, CH340/CH341 et Prolific.

## 3. Vérifier si macOS voit le matériel

Dans Terminal, relever les ports avant de brancher la balance :

```sh
ls /dev/cu.*
```

Brancher toute la chaîne, attendre quelques secondes, puis relancer la même commande. Un nouveau nom devrait apparaître, par exemple :

- `/dev/cu.usbserial-...`
- `/dev/cu.usbmodem...`
- `/dev/cu.SLAB_USBtoUART`
- `/dev/cu.wchusbserial...`

On peut aussi inspecter les périphériques USB reconnus :

```sh
system_profiler SPUSBDataType
```

### Interprétation

- **Aucun changement dans `/dev/cu.*` et rien dans `system_profiler`** : adaptateur USB-C, câble, hub, alimentation ou connexion physique.
- **Matériel visible dans `system_profiler`, mais aucun nouveau `/dev/cu.*`** : pilote du chipset USB–série probablement absent ou incompatible.
- **Nouveau `/dev/cu.*`, mais absent de l’application** : filtre de détection de l’application trop restrictif ; noter le nom exact du port pour corriger le filtre.
- **Port visible dans l’application** : passer à l’étape suivante.

## 4. Vérifier si le port s’ouvre

Fermer préalablement tout logiciel pouvant utiliser la liaison série : terminal série, logiciel Ohaus, autre copie du collecteur ou outil de diagnostic.

Lancer la collecte et observer l’indicateur :

- **Port série ouvert – attente de la balance** : le pilote fonctionne et le port n’est pas occupé.
- **Resource busy / Device busy** : un autre programme utilise le port. Fermer les autres programmes ou redémarrer le Mac.
- **Permission denied** : problème de droits ou de pilote.
- **No such file or directory** : périphérique débranché ou nom de port devenu invalide.

## 5. Tester la réponse brute de la balance

Le dépôt contient `balance/diagnose_serial.py`. Depuis la racine du dépôt, remplacer le port de l’exemple par celui observé à l’étape 3 :

```sh
python3 balance/diagnose_serial.py /dev/cu.usbserial-XXXX
```

Le script :

1. écoute les éventuelles données spontanées pendant cinq secondes ;
2. envoie la commande `SI` ;
3. envoie la commande `S` ;
4. affiche les octets reçus en hexadécimal et en ASCII.

Si le module `serial` manque :

```sh
python3 -m pip install pyserial
```

### Interprétation

- **Aucune donnée spontanée et aucune réponse aux commandes** : vérifier le câble, les paramètres de la balance et le protocole configuré.
- **Une réponse apparaît** : copier intégralement les lignes `HEX` et `ASCII`; elles permettront d’adapter précisément le lecteur.
- **La réponse contient un poids, mais l’interface indique “trame inconnue”** : la liaison fonctionne, mais le format reçu n’est pas reconnu par l’analyseur.
- **Réponse `ES` ou `S I`** : la balance répond, mais refuse ou ne comprend pas la commande envoyée.

## 6. Examiner le journal CSV et les erreurs

Les mesures et trames brutes sont enregistrées ici :

```text
~/Documents/BalanceCollecteur/data balance/balance.csv
```

Les informations importantes sont les colonnes :

- `raw_frame` : réponse exacte reçue ;
- `status` : `ok`, `vide`, `trame inconnue`, surcharge, etc. ;
- `weight_g` : poids converti en grammes lorsque la trame est reconnue.

Si l’application ne démarre pas, consulter :

```text
~/Documents/BalanceCollecteur/error.log
```

## 7. Réinstaller ou reconstruire la bonne version macOS

L’installation automatique télécharge puis construit la version macOS :

```sh
bash balance/install_mac.sh
```

Pour construire depuis le dépôt déjà cloné :

```sh
bash balance/build_macos.sh
```

Le script de construction utilise `balance/balance_gui_macos.py`. Après un `git pull`, il faut reconstruire/réinstaller l’application pour que les modifications du code soient présentes dans l’application `.app`.

## Informations à transmettre si le problème persiste

Envoyer les éléments suivants :

1. modèle et année du Mac, processeur Intel ou Apple Silicon ;
2. version de macOS ;
3. référence ou photo de l’adaptateur USB–série et de l’adaptateur USB-C ;
4. résultat de `ls /dev/cu.*` avant et après branchement ;
5. dernier message de connexion affiché dans l’application ;
6. sortie complète de `diagnose_serial.py` ;
7. quelques lignes du CSV contenant `raw_frame` et `status`.
