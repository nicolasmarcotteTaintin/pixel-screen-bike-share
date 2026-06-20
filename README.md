# àVélo Pixoo 64 Display

Petit daemon Python pour Raspberry Pi OS Lite qui affiche des stations [àVélo](https://www.avelo.ca) (le reseau de velos en libre-service de la Ville de Quebec, opere par le RTC) en temps reel sur un Divoom Pixoo 64.

àVélo est un reseau **100% electrique** : l'affichage montre donc deux colonnes par station, les **velos** disponibles et les **bornes** libres (pas de colonne velo electrique separee, contrairement a BIXI).

![Exemple - Place Laurier](example-place-laurier.png)

Exemple ci-dessus : les 3 stations les plus proches de **Place Laurier** (Sainte-Foy) un apres-midi.

Le flux de donnees est le GBFS v3 d'àVélo :
`https://quebec.publicbikesystem.net/customer/gbfs/v3.0/gbfs.json`

Copie `config.example.json` vers `config.json` puis renseigne tes stations (les `station_id` GBFS d'àVélo, par ex. `81` = Samuel-King / Quatre-Bourgeois). `config.json` est ignore par git.

## Materiel

| Composant | Lien | Prix approx. (CAD) |
|-----------|------|--------------------|
| Divoom Pixoo 64 (ecran 64x64 pixels) | [Addison Electronique](https://addison-electronique.com/fr/catalogsearch/result/?q=pixoo) | ~80 $ |
| Raspberry Pi Zero 2 W | [Amazon](https://www.amazon.ca/s?k=Raspberry+Pi+Zero+2+W) | ~25 $ |
| Boitier pour Pi Zero 2 W *(optionnel)* | [Amazon](https://www.amazon.ca/s?k=Raspberry+Pi+Zero+2+W+case) | ~10 $ |

**Cout total : ~105 $ CAD** (~115 $ avec le boitier).

> Prix indicatifs, sujets a variation. Une carte microSD et une alimentation USB pour le Pi sont aussi necessaires (souvent deja a la maison).

## Installation sur le Pi

```bash
cp config.example.json config.json   # puis edite favorite_stations
sudo mkdir -p /opt/avelo-display
sudo cp main.py pixoo.py config.json requirements.txt bixi-display.service avelo_logo_27.png /opt/avelo-display/
sudo chown -R "$USER":"$USER" /opt/avelo-display
cd /opt/avelo-display
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
sudo cp bixi-display.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bixi-display.service
```

Si `zeroconf` ne trouve pas le Pixoo, force l'adresse IP:

```bash
sudo systemctl edit bixi-display.service
```

Puis ajoute:

```ini
[Service]
Environment=PIXOO_IP=192.168.1.123
```

## Mode setup

```bash
cd /opt/avelo-display
.venv/bin/python main.py --setup
```

Ouvre ensuite `http://adresse-du-pi:8080`.

## Test local

```bash
.venv/bin/python main.py --once --preview preview.png
```

Les logs vont dans `/var/log/bixi-display.log`. Si le processus n'a pas le droit d'ecrire dans `/var/log`, le code bascule vers `bixi-display.log` dans le dossier de l'application.
