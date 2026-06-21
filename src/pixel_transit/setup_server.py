"""Local Flask setup page to edit the configuration from a phone or laptop."""

from __future__ import annotations

import logging
from html import escape
from typing import Any

from flask import Flask, redirect, request

from .config import load_config, save_config
from .providers.registry import BIKE_NETWORKS

MODE_LABELS = {
    "velo": "1. Vélo uniquement",
    "velo_communauto": "2. Vélo + Communauto (alternance)",
    "communauto": "3. Communauto uniquement",
}


def run_setup_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        return _render_page(load_config(), escape(request.args.get("saved", "")))

    @app.post("/")
    def save() -> Any:
        config = load_config()
        config["mode"] = request.form.get("mode", config["mode"]).lower()
        config["network"] = request.form.get("network", config["network"]).lower()
        config["rotate_seconds"] = max(2, _int(request.form.get("rotate_seconds"), 10))
        config["favorite_stations"] = [
            line.strip()
            for line in request.form.get("favorite_stations", "").splitlines()
            if line.strip()
        ]
        config["refresh_seconds"] = max(10, min(3600, _int(request.form.get("refresh_seconds"), 60)))
        config["brightness"] = max(0, min(100, _int(request.form.get("brightness"), 80)))
        config["off_start"] = request.form.get("off_start", "").strip()
        config["off_end"] = request.form.get("off_end", "").strip()

        communauto = config.setdefault("communauto", {})
        communauto["city_id"] = _int(request.form.get("city_id"), communauto.get("city_id", 59))
        communauto.setdefault("home", {})
        communauto["home"]["lat"] = _float(request.form.get("home_lat"), communauto["home"].get("lat", 45.5019))
        communauto["home"]["lon"] = _float(request.form.get("home_lon"), communauto["home"].get("lon", -73.5674))
        communauto["radius_km"] = _float(request.form.get("radius_km"), communauto.get("radius_km", 2.0))
        communauto["services"] = request.form.getlist("services") or ["flex", "station"]

        save_config(config)
        logging.info("Configuration saved from setup server")
        return redirect("/?saved=Configuration%20sauvegardee")

    app.run(host=host, port=port)


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _render_page(config: dict[str, Any], message: str) -> str:
    stations = escape("\n".join(config.get("favorite_stations", [])))
    communauto = config.get("communauto", {})
    home = communauto.get("home", {})
    services = communauto.get("services", ["flex", "station"])
    mode_options = "\n".join(
        f'<option value="{key}"{" selected" if key == config["mode"] else ""}>{label}</option>'
        for key, label in MODE_LABELS.items()
    )
    bike_options = "\n".join(
        f'<option value="{n}"{" selected" if n == config["network"] else ""}>{n}</option>'
        for n in BIKE_NETWORKS
    )
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pixel Transit setup</title>
  <style>
    body {{ background: #111; color: #f5f5f5; font-family: system-ui, sans-serif; margin: 2rem; }}
    main {{ max-width: 36rem; margin: auto; }}
    label {{ display: block; margin-top: 1rem; font-weight: 700; }}
    textarea, input, select {{ box-sizing: border-box; width: 100%; padding: .7rem; margin-top: .35rem; border: 1px solid #555; border-radius: 8px; background: #1f1f1f; color: white; }}
    fieldset {{ margin-top: 1rem; border: 1px solid #444; border-radius: 8px; }}
    .row {{ display: flex; gap: .75rem; }}
    .row > div {{ flex: 1; }}
    button {{ margin-top: 1.25rem; padding: .8rem 1rem; border: 0; border-radius: 8px; background: #38a169; color: white; font-weight: 700; }}
    .saved {{ color: #68d391; min-height: 1.5rem; }}
    .hint {{ color: #999; font-weight: 400; font-size: .85rem; }}
  </style>
</head>
<body>
  <main>
    <h1>Pixel Transit</h1>
    <p class="saved">{message}</p>
    <form method="post">
      <label for="mode">Mode d'affichage</label>
      <select id="mode" name="mode">{mode_options}</select>

      <label for="rotate_seconds">Alternance, secondes <span class="hint">(mode 2)</span></label>
      <input id="rotate_seconds" name="rotate_seconds" type="number" min="2" max="600" value="{config.get('rotate_seconds', 10)}">

      <fieldset>
        <legend>Vélos en libre-service</legend>
        <label for="network">Système de vélos</label>
        <select id="network" name="network">{bike_options}</select>
        <label for="favorite_stations">Stations favorites, une par ligne <span class="hint">(station_id ou short_name)</span></label>
        <textarea id="favorite_stations" name="favorite_stations" rows="5">{stations}</textarea>
      </fieldset>

      <fieldset>
        <legend>Communauto</legend>
        <label for="city_id">City ID <span class="hint">(59 = Montréal)</span></label>
        <input id="city_id" name="city_id" type="number" value="{communauto.get('city_id', 59)}">
        <div class="row">
          <div>
            <label for="home_lat">Latitude (maison)</label>
            <input id="home_lat" name="home_lat" type="text" value="{home.get('lat', 45.5019)}">
          </div>
          <div>
            <label for="home_lon">Longitude (maison)</label>
            <input id="home_lon" name="home_lon" type="text" value="{home.get('lon', -73.5674)}">
          </div>
        </div>
        <label for="radius_km">Rayon de recherche (km)</label>
        <input id="radius_km" name="radius_km" type="text" value="{communauto.get('radius_km', 2.0)}">
        <label>Services</label>
        <label class="hint"><input type="checkbox" name="services" value="flex" {"checked" if "flex" in services else ""}> FLEX (libre-service)</label>
        <label class="hint"><input type="checkbox" name="services" value="station" {"checked" if "station" in services else ""}> Stations (aller-retour)</label>
      </fieldset>

      <label for="refresh_seconds">Rafraîchissement, secondes</label>
      <input id="refresh_seconds" name="refresh_seconds" type="number" min="10" max="3600" value="{config['refresh_seconds']}">

      <label for="brightness">Luminosité, 0 à 100</label>
      <input id="brightness" name="brightness" type="number" min="0" max="100" value="{config['brightness']}">

      <fieldset>
        <legend>Heures d'extinction <span class="hint">(écran éteint dans cette plage ; laisser vide pour désactiver)</span></legend>
        <div class="row">
          <div>
            <label for="off_start">Éteindre à</label>
            <input id="off_start" name="off_start" type="time" value="{config.get('off_start', '')}">
          </div>
          <div>
            <label for="off_end">Rallumer à</label>
            <input id="off_end" name="off_end" type="time" value="{config.get('off_end', '')}">
          </div>
        </div>
      </fieldset>

      <button type="submit">Sauvegarder</button>
    </form>
  </main>
</body>
</html>"""
