# Pixel Transit — Pixoo 64 Display

Daemon Python pour Raspberry Pi OS Lite qui affiche, en temps réel, l'état d'un
réseau de transport partagé sur un écran LED **Divoom Pixoo 64** (64×64 pixels).

Trois réseaux sont supportés, sélectionnables dans `config.json` :

| Réseau | Type | Ce qui est affiché |
|--------|------|--------------------|
| **BIXI** (Montréal) | Vélos en libre-service | Par station : vélos méca, vélos électriques ⚡, bornes libres |
| **àVélo** (Québec) | Vélos 100% électriques | Par station : vélos disponibles, bornes libres |
| **Communauto** | Autopartage (FLEX + stations) | Autos proches : **distance** + **localisation** (nom de station, ou direction pour les FLEX) |

![Exemple àVélo - Place Laurier](docs/example-place-laurier.png)

## Matériel

| Composant | Lien | Prix approx. (CAD) |
|-----------|------|--------------------|
| Divoom Pixoo 64 (écran 64×64) | [Addison Électronique](https://addison-electronique.com/fr/catalogsearch/result/?q=pixoo) | ~80 $ |
| Raspberry Pi Zero 2 W | [Amazon](https://www.amazon.ca/s?k=Raspberry+Pi+Zero+2+W) | ~25 $ |
| Boîtier pour Pi Zero 2 W *(optionnel)* | [Amazon](https://www.amazon.ca/s?k=Raspberry+Pi+Zero+2+W+case) | ~10 $ |

**Coût total : ~105 $ CAD** (~115 $ avec le boîtier).

> Prix indicatifs, sujets à variation. Une carte microSD et une alimentation USB
> pour le Pi sont aussi nécessaires (souvent déjà à la maison).

## Structure du projet

```
pixel-screen-bike-share/
├── pyproject.toml              # package + dépendances
├── config.example.json        # config d'exemple (copier vers config.json)
├── deploy/
│   └── pixel-transit.service   # unité systemd
├── docs/                       # captures d'écran
├── tests/                      # tests unitaires
└── src/pixel_transit/
    ├── cli.py / __main__.py    # point d'entrée (`python -m pixel_transit`)
    ├── app.py                  # boucle d'affichage
    ├── config.py               # chargement / validation de la config
    ├── geo.py                  # distance, direction (Communauto)
    ├── pixoo.py                # API LAN du Pixoo (découverte + envoi d'image)
    ├── setup_server.py         # page de configuration Flask
    ├── wifi.py / status.py     # diagnostics
    ├── assets/                 # logos PNG
    ├── providers/              # une source de données par réseau
    │   ├── base.py             # interface Provider + modèles de vue
    │   ├── gbfs.py             # logique GBFS partagée (BIXI, àVélo)
    │   ├── bixi.py / avelo.py
    │   ├── communauto.py       # API Reservauto (FLEX + stations)
    │   └── registry.py         # nom de réseau → provider
    └── rendering/              # dessin sur le canevas 64×64
        ├── fonts.py / icons.py / common.py
        ├── bikeshare.py        # vue tableau (vélos)
        └── carshare.py         # vue distances/localisation (Communauto)
```

Ajouter un réseau = écrire un provider qui renvoie un modèle de vue ; aucun autre
fichier n'a besoin d'être modifié.

## Configuration

Copie `config.example.json` vers `config.json` et choisis le réseau :

```json
{
  "network": "avelo",
  "mode": "velo_communauto",
  "rotate_seconds": 10,
  "favorite_stations": ["81", "85", "141"],
  "communauto": {
    "city_id": 90,
    "home": { "lat": 46.7803, "lon": -71.2900 },
    "radius_km": 2.0,
    "services": ["flex", "station"],
    "max_rows": 3
  },
  "refresh_seconds": 60,
  "brightness": 80,
  "off_start": "21:00",
  "off_end": "08:00"
}
```

- **`mode`** : option d'intégration affichée sur le module —
  1. `"velo"` : vélo uniquement ;
  2. `"velo_communauto"` : vélo + Communauto en alternance (chaque `rotate_seconds`) ;
  3. `"communauto"` : Communauto uniquement.
- **`rotate_seconds`** : durée de chaque écran en mode alternance (défaut 10 s).
- **`network`** : le système de vélos utilisé pour le côté « vélo » — `"bixi"` ou `"avelo"`.
- **`off_start` / `off_end`** : plage d'extinction de l'écran (format `"HH:MM"`,
  24 h, peut traverser minuit). L'écran s'éteint à `off_start` et se rallume à
  `off_end`. Laisser les deux vides pour désactiver. Ex. `21:00` → `08:00`.
- **`favorite_stations`** (BIXI/àVélo) : `station_id` GBFS ou `short_name` public
  (ex. `6026` pour BIXI, `81` pour àVélo).
- **`communauto`** :
  - `city_id` : `59` = Montréal (modifiable pour d'autres villes Communauto).
  - `home` : point de référence pour calculer la **distance**.
  - `radius_km` : rayon de recherche autour de `home`.
  - `services` : `"flex"` (libre-service) et/ou `"station"` (aller-retour).

`config.json` est ignoré par git.

## Installation sur le Pi

```bash
cp config.example.json config.json     # puis édite-le
sudo mkdir -p /opt/pixel-transit
sudo cp -r src pyproject.toml requirements.txt config.json deploy /opt/pixel-transit/
sudo chown -R "$USER":"$USER" /opt/pixel-transit
cd /opt/pixel-transit
python3 -m venv .venv
.venv/bin/pip install -e .
sudo cp deploy/pixel-transit.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pixel-transit.service
```

Si `zeroconf` ne trouve pas le Pixoo, force l'adresse IP :

```bash
sudo systemctl edit pixel-transit.service
```

```ini
[Service]
Environment=PIXOO_IP=192.168.1.123
```

## Mode setup (page web)

```bash
cd /opt/pixel-transit
.venv/bin/python -m pixel_transit --setup
```

Ouvre ensuite `http://adresse-du-pi:8080` pour choisir le réseau, les stations
favorites, le point « maison » Communauto, le rafraîchissement et la luminosité.

## Test local (aperçu PNG)

```bash
.venv/bin/python -m pixel_transit --once --preview preview.png
```

Rend une frame avec la config courante et l'écrit dans `preview.png` (pas besoin
d'un Pixoo connecté).

## Logs et diagnostic

Les logs vont dans `/var/log/pixel-transit.log` (repli vers le dossier de
l'app si non accessible en écriture). Un instantané de santé est écrit dans
`status.json` — `cat status.json` pour diagnostiquer rapidement.

## Écran LCD 1,3" (menu de sélection du mode) — *préparé, pas encore intégré*

Code prêt pour un **écran IPS 1,3" 240×240 (ST7789, SPI)** — typiquement le
*Waveshare 1.3inch LCD HAT* (joystick + 3 touches). Il affiche d'abord un menu de
**langue** (Français / English), puis un **menu de réglages** (localisé) :
**Mode d'affichage**, **Luminosité** (curseur 0–100 %) et **Langue**. Les choix
sont écrits dans `config.json` (`language`, `mode`, `brightness`) — la luminosité
est reprise en direct par le daemon. Ce module est
isolé dans [src/pixel_transit/lcd/](src/pixel_transit/lcd/) et **n'est pas branché**
sur le daemon d'affichage Pixoo ; il se lance séparément.

Aperçu du menu sans matériel :

```bash
.venv/bin/python -m pixel_transit.lcd --preview menu.png --active velo_communauto
```

Sur le Pi (active le SPI avec `sudo raspi-config` → Interface Options → SPI) :

```bash
.venv/bin/pip install -e ".[lcd]"     # spidev, RPi.GPIO, numpy
.venv/bin/python -m pixel_transit.lcd
```

Commandes : joystick haut/bas pour naviguer, **OK** (clic joystick) pour valider ;
**KEY1/KEY2/KEY3** sélectionnent directement l'option 1/2/3. Brochage (BCM) par
défaut du HAT dans [st7789.py](src/pixel_transit/lcd/st7789.py) et
[buttons.py](src/pixel_transit/lcd/buttons.py).

## Sécurité

- **Mot de passe Wi‑Fi** : l'application ne le manipule **jamais**. [wifi.py](src/pixel_transit/wifi.py)
  lit uniquement le *nom* du réseau (SSID) pour l'afficher ; aucun mot de passe n'est
  lu, stocké ni journalisé. Le SSID (nom seulement) apparaît dans `status.json`.
- **Stockage du mot de passe (niveau OS)** : c'est Raspberry Pi OS qui le garde, **en
  clair sur la carte SD**, lisible par `root` seulement
  (`/etc/NetworkManager/system-connections/*.nmconnection`, ou
  `/etc/wpa_supplicant/wpa_supplicant.conf` sur les versions plus anciennes). Le Pi n'a
  pas de puce sécurisée : **quiconque a la carte SD peut lire le mot de passe.** Une
  image `.img` de sauvegarde le contient aussi.
- **SSH** : si activé, change le mot de passe par défaut (`pi`/`raspberry`) ou utilise
  des clés. Un accès SSH root permet de lire le `psk` — c'est souvent le vrai maillon
  faible, avant le vol de carte.
- **Serveur de setup** : `--setup` écoute sur `0.0.0.0:8080` **sans authentification**.
  Il n'expose pas le mot de passe Wi‑Fi, mais permet de changer la config depuis le LAN.
  Ne le lance que ponctuellement, puis arrête‑le (ne pas laisser tourner en permanence).
- **Réseau dédié** : place le Pi sur un SSID/VLAN invité ou IoT séparé pour limiter
  l'impact en cas de compromission.

Pour un usage maison (pas d'accès physique, SSH désactivé ou protégé, setup lancé au
besoin), le risque est faible.

## Tests

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
```
