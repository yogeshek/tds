import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

BASE = Path(__file__).parent
APP_ENV = os.getenv("APP_ENV", "development")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

ALIASES = {"num_workers": "workers"}


def norm_key(k: str) -> str:
    k = k.strip().lower()
    if k.startswith("app_"):
        k = k[4:]
    return ALIASES.get(k, k)


def coerce(key, val):
    if key in ("port", "workers"):
        return int(str(val).strip())
    if key == "debug":
        if isinstance(val, bool):
            return val
        return str(val).strip().lower() in ("true", "1", "yes", "on")
    return str(val)


def load_yaml():
    f = BASE / f"config.{APP_ENV}.yaml"
    if f.exists():
        data = yaml.safe_load(f.read_text()) or {}
        return {norm_key(k): v for k, v in data.items()}
    return {}


def load_dotenv_layer():
    # dotenv_values reads the file WITHOUT polluting os.environ
    data = dotenv_values(BASE / ".env")
    out = {}
    for k, v in data.items():
        if v is None:
            continue
        if k.upper().startswith("APP_") or k.upper() == "NUM_WORKERS":
            out[norm_key(k)] = v
    return out


def load_os_env():
    return {norm_key(k): v for k, v in os.environ.items() if k.upper().startswith("APP_")
            and k.upper() != "APP_ENV"}


@app.get("/effective-config")
def effective_config(request: Request):
    cfg = dict(DEFAULTS)
    for layer in (load_yaml(), load_dotenv_layer(), load_os_env()):
        cfg.update(layer)

    # CLI overrides: ?set=key=value (repeatable), highest precedence
    for item in request.query_params.getlist("set"):
        if "=" in item:
            k, v = item.split("=", 1)
            cfg[norm_key(k)] = v

    result = {}
    for k, v in cfg.items():
        try:
            result[k] = coerce(k, v)
        except ValueError:
            result[k] = DEFAULTS.get(k)
    result["api_key"] = "****"
    return result
