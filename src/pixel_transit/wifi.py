"""Best-effort detection of the connected Wi-Fi SSID across platforms."""

from __future__ import annotations

import subprocess


def get_wifi_ssid() -> str | None:
    """Return the connected Wi-Fi SSID, or None if not connected/unknown."""
    commands = [
        ["iwgetid", "-r"],
        ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
        ["networksetup", "-getairportnetwork", "en0"],
    ]
    for command in commands:
        try:
            output = subprocess.run(
                command, capture_output=True, text=True, timeout=3
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if not output:
            continue
        if command[0] == "iwgetid":
            return output
        if command[0] == "nmcli":
            for line in output.splitlines():
                if line.startswith("yes:"):
                    ssid = line.split(":", 1)[1].strip()
                    if ssid:
                        return ssid
            continue
        if command[0] == "networksetup":
            marker = "Current Wi-Fi Network: "
            if output.startswith(marker):
                return output[len(marker):].strip()
    return None
