"""
Configuración de JWT cargada desde config.yaml.
"""

from __future__ import annotations

import yaml


def _cargar_config() -> dict:
    with open("config.yaml", "r") as archivo:
        return yaml.safe_load(archivo)


_config = _cargar_config()

JWT_SECRET_KEY: str = _config["jwt"]["secret_key"]
JWT_ALGORITHM: str = _config["jwt"]["algorithm"]
JWT_EXPIRES_DAYS: int = int(_config["jwt"]["expires_days"])