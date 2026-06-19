# BIXI Pixoo 64 Display

Petit daemon Python pour Raspberry Pi OS Lite qui affiche des stations BIXI en temps reel sur un Divoom Pixoo 64.

Copie `config.example.json` vers `config.json` puis renseigne tes stations. Le fichier accepte les `station_id` GBFS et les `short_name` BIXI publics comme `6026`. `config.json` est ignore par git (il contient tes vraies stations).

## Installation sur le Pi

```bash
cp config.example.json config.json   # puis edite favorite_stations
sudo mkdir -p /opt/bixi-display
sudo cp main.py pixoo.py config.json requirements.txt bixi-display.service Bixi_logo2.png Bixi_logo2_27.png /opt/bixi-display/
sudo chown -R "$USER":"$USER" /opt/bixi-display
cd /opt/bixi-display
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
cd /opt/bixi-display
.venv/bin/python main.py --setup
```

Ouvre ensuite `http://adresse-du-pi:8080`.

## Test local

```bash
.venv/bin/python main.py --once --preview preview.png
```

Les logs vont dans `/var/log/bixi-display.log`. Si le processus n'a pas le droit d'ecrire dans `/var/log`, le code bascule vers `bixi-display.log` dans le dossier de l'application.
