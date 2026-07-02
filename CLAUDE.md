# CLAUDE.md — guide pour un outil AI

Ce fichier est chargé automatiquement à chaque session. Il décrit **toute la chaîne**,
du poste de dev jusqu'aux deux écrans physiques, pour qu'un assistant comprenne vite
comment les pièces s'emboîtent. Détails complémentaires : voir `README.md` (orienté
utilisateur) et la mémoire locale de l'agent (host/IP/identifiants du Pi réel).

## Vue d'ensemble : la chaîne complète

```
  MAC (dev)                        RASPBERRY PI Zero 2 W                 MATÉRIEL
  ─────────                        ─────────────────────                ────────
  éditer le code                   2 services systemd (User=nmarcotte)
  lancer les tests    ── deploy ─▶ ├─ pixel-transit.service ───HTTP LAN─▶ Pixoo 64 (64×64 LED)
  rendre des previews  (tar/ssh)   │    = python3 -m pixel_transit         → données transit
  (git vit ICI)                    └─ pixel-transit-lcd.service ─SPI/GPIO▶ LCD ST7789 1,3" 240×240
                                        = python3 -m pixel_transit.lcd      → menu de réglages
                                   les 2 services partagent config.json
```

- **Le code source (git) vit sur le Mac.** Le Pi n'a **pas** git : on y **déploie** une copie.
- **Deux sous-systèmes indépendants** tournent sur le Pi, chacun son service systemd,
  reliés uniquement par `config.json` (le menu LCD écrit les réglages, le daemon Pixoo les lit).

## Les deux points d'entrée

| Commande | Fichier | Rôle |
|---|---|---|
| `python -m pixel_transit` | [cli.py](src/pixel_transit/cli.py) → [app.py](src/pixel_transit/app.py) | Daemon Pixoo 64 : fetch données → rend 64×64 → POST HTTP au Pixoo |
| `python -m pixel_transit.lcd` | [lcd/__main__.py](src/pixel_transit/lcd/__main__.py) → [lcd/controller.py](src/pixel_transit/lcd/controller.py) | Menus sur l'écran ST7789 (langue, mode, luminosité, veille) via SPI + boutons GPIO |

Ajouter un réseau transit = écrire un provider dans [providers/](src/pixel_transit/providers/)
(interface dans [base.py](src/pixel_transit/providers/base.py), enregistré dans
[registry.py](src/pixel_transit/providers/registry.py)) ; rien d'autre à toucher.

## Travailler sur le code (sur le Mac, sans matériel)

```bash
# Le package n'est pas installé dans .venv → lancer avec PYTHONPATH=src
PYTHONPATH=src .venv/bin/python -m pytest                      # tests
PYTHONPATH=src .venv/bin/python -m pixel_transit.lcd --preview /tmp/menu.png --screen main   # aperçu menu LCD (PNG)
PYTHONPATH=src .venv/bin/python -m pixel_transit --once --preview /tmp/pixoo.png              # aperçu frame Pixoo (PNG)
```

Les `--preview` ne demandent aucun matériel : c'est le moyen de valider le rendu avant de déployer.

## Déployer sur le Pi

Pas de git sur le Pi → on pousse les fichiers par `tar`-over-ssh (voir la mémoire de l'agent
pour l'host/user exacts) :

```bash
tar czf - src config.json pyproject.toml | ssh <pi> 'rm -rf ~/pixel-transit && mkdir -p ~/pixel-transit && tar xzf - -C ~/pixel-transit'
ssh <pi> 'sudo systemctl restart pixel-transit.service pixel-transit-lcd.service'
```

## Runtime sur le Pi (important : diffère du README)

Le `README.md` décrit un déploiement idéalisé (`/opt/pixel-transit` + venv + `pip install -e ".[lcd]"`).
**Le Pi réel ne fait PAS ça** — sur Raspbian 13 (Trixie), pip est bridé (PEP 668) et
`RPi.GPIO` est peu fiable. Le déploiement effectif :

- Code dans `~/pixel-transit`, lancé par le **python système** (`/usr/bin/python3`) avec
  `PYTHONPATH=~/pixel-transit/src` et `PIXEL_TRANSIT_CONFIG_PATH=~/pixel-transit/config.json`.
- Dépendances installées via **apt**, pas pip :
  - LCD : `python3-spidev python3-rpi-lgpio python3-numpy python3-pil fonts-dejavu-core`
  - Daemon : `python3-requests python3-zeroconf python3-flask`
- **`rpi-lgpio`** fournit un `import RPi.GPIO` compatible (l'original casse sur Trixie).
  [lcd/st7789.py](src/pixel_transit/lcd/st7789.py) et [lcd/buttons.py](src/pixel_transit/lcd/buttons.py)
  importent `RPi.GPIO` sans le savoir.
- SPI activé (`sudo raspi-config nonint do_spi 0` + reboot → `/dev/spidev0.0`).
- Les 2 services tournent en `User=nmarcotte` (membre des groupes `gpio`/`spi` → pas besoin de root).

## Flux de config

`config.json` est la source de vérité partagée. Le menu LCD y écrit `language`, `mode`,
`brightness`, `off_enabled`/`off_start`/`off_end` ([lcd/controller.py](src/pixel_transit/lcd/controller.py)).
Le daemon Pixoo recharge `config.json` **à chaque cycle** ([app.py](src/pixel_transit/app.py) `load_config()`)
et applique luminosité + veille en direct. Chemin résolu par `PIXEL_TRANSIT_CONFIG_PATH`
([config.py](src/pixel_transit/config.py)). L'IP du Pixoo vient de `config.json["pixoo_ip"]`
(sinon découverte zeroconf, sinon env `PIXOO_IP`).

## Pièges à connaître

- **Rien ne s'affiche sur le LCD ?** Le module LCD est autonome : il faut que
  `pixel-transit-lcd.service` tourne ET que le SPI soit activé. Un écran noir ≠ bug code.
- **Le Pi disparaît du réseau / LED verte fixe** → souvent **carte SD corrompue**
  (pas forcément l'alim ; vérifier `vcgencmd get_throttled`, `0x0` = alim OK). IP en DHCP,
  peut changer : résoudre via `bixi-pixoo.local`.
- **Modifs de code** → il FAUT redéployer (tar/ssh) puis `systemctl restart`, le Pi ne suit pas git.
- Diagnostics : `systemctl status pixel-transit{,-lcd}.service` ; `journalctl -u <svc> -f` ;
  `status.json` (instantané de santé écrit par le daemon).
