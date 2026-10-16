"""Configure l'envoi Balance Mac vers le Node-RED local."""
from __future__ import annotations

import json
import os
import plistlib
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BASE = Path.home() / "Applications" / "IrrigationServer"
SECRETS_PATH = BASE / "config" / "connexion-influx.json"
LAUNCH_AGENT = (
    Path.home() / "Library" / "LaunchAgents" / "org.ird.irrigation.nodered.plist"
)
FLOW_PATH = Path(__file__).with_name("flow_balance_mac.json")
INFLUX_URL = "http://127.0.0.1:8086"
NODE_RED_URL = "http://127.0.0.1:1880"


def request_json(url: str, method: str = "GET", body: Any = None,
                 token: str | None = None, headers: dict | None = None):
    request_headers = {"Accept": "application/json"}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    if token:
        request_headers["Authorization"] = f"Token {token}"
    if headers:
        request_headers.update(headers)
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers=request_headers, method=method
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        content = response.read()
        return response.status, json.loads(content) if content else None


def write_private_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def wait_for_node_red() -> None:
    last_error = None
    for _ in range(20):
        try:
            request_json(NODE_RED_URL + "/flows")
            return
        except (OSError, urllib.error.URLError) as error:
            last_error = error
            time.sleep(1)
    raise RuntimeError(f"Node-RED ne repond pas sur localhost:1880 ({last_error})")


def configure_writer_token(secrets: dict) -> str:
    token = secrets.get("balanceWriteToken")
    if token:
        return token

    status, response = request_json(
        INFLUX_URL + "/api/v2/buckets?org=ird&name=sondes",
        token=secrets["adminToken"],
    )
    bucket = next(
        (item for item in response.get("buckets", []) if item.get("name") == "sondes"),
        None,
    )
    if not bucket:
        raise RuntimeError("Bucket InfluxDB 'sondes' introuvable dans l'organisation ird.")

    _, authorization = request_json(
        INFLUX_URL + "/api/v2/authorizations",
        method="POST",
        token=secrets["adminToken"],
        body={
            "orgID": bucket["orgID"],
            "description": "Node-RED balance Mac - ecriture bucket sondes",
            "permissions": [{
                "action": "write",
                "resource": {
                    "type": "buckets",
                    "id": bucket["id"],
                    "orgID": bucket["orgID"],
                },
            }],
        },
    )
    token = authorization.get("token")
    if not token:
        raise RuntimeError("InfluxDB n'a pas retourne de jeton d'ecriture.")
    secrets["balanceWriteToken"] = token
    write_private_json(SECRETS_PATH, secrets)
    return token


def update_node_red_environment(token: str) -> None:
    if not LAUNCH_AGENT.is_file():
        raise RuntimeError(f"Service Node-RED introuvable : {LAUNCH_AGENT}")
    with LAUNCH_AGENT.open("rb") as file:
        launch_config = plistlib.load(file)
    environment = launch_config.setdefault("EnvironmentVariables", {})
    environment["INFLUX_TOKEN"] = token
    temporary = LAUNCH_AGENT.with_suffix(".plist.tmp")
    with temporary.open("wb") as file:
        plistlib.dump(launch_config, file)
    temporary.chmod(0o600)
    os.replace(temporary, LAUNCH_AGENT)

    domain = f"gui/{os.getuid()}"
    subprocess.run(
        ["/bin/launchctl", "bootout", domain, str(LAUNCH_AGENT)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["/bin/launchctl", "bootstrap", domain, str(LAUNCH_AGENT)],
        check=True,
    )


def deploy_flow() -> None:
    if not FLOW_PATH.is_file():
        raise RuntimeError(f"Flux Node-RED introuvable : {FLOW_PATH}")
    new_nodes = json.loads(FLOW_PATH.read_text(encoding="utf-8"))
    new_ids = {node["id"] for node in new_nodes}
    tab_id = next(node["id"] for node in new_nodes if node.get("type") == "tab")
    _, current = request_json(NODE_RED_URL + "/flows")
    if isinstance(current, dict):
        current = current.get("flows", [])
    if not isinstance(current, list):
        raise RuntimeError("Format inattendu retourne par l'API Node-RED /flows.")
    merged = [
        node for node in current
        if node.get("id") not in new_ids and node.get("z") != tab_id
    ]
    merged.extend(new_nodes)
    request_json(
        NODE_RED_URL + "/flows",
        method="POST",
        body=merged,
        headers={"Node-RED-Deployment-Type": "full"},
    )


def main() -> int:
    if not SECRETS_PATH.is_file():
        raise RuntimeError(f"Fichier InfluxDB prive introuvable : {SECRETS_PATH}")
    secrets = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    if not secrets.get("adminToken"):
        raise RuntimeError("Le fichier local ne contient pas adminToken.")
    if not FLOW_PATH.is_file():
        raise RuntimeError("Le fichier flow_balance_mac.json doit etre dans le meme dossier.")

    writer_token = configure_writer_token(secrets)
    update_node_red_environment(writer_token)
    wait_for_node_red()
    deploy_flow()
    print("Flux balance installe dans Node-RED, autres onglets conserves.")
    print("Jeton d'ecriture limite au bucket sondes et conserve dans le fichier prive local.")
    print("Adresse locale de reception : http://127.0.0.1:1880/balance/measurement")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Configuration impossible : {error}", file=__import__("sys").stderr)
        raise SystemExit(1)