from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import time
import json
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BLAZE_URL = "https://blaze.bet.br/api/singleplayer-originals/originals/roulette_games/recent/1"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://blaze.bet.br/pt/games/double",
}

CACHE_SECONDS = 5
JSON_PATH = Path("resultados.json")

cache = {
    "data": [],
    "last_update": 0.0
}


def map_cor(color, numero):
    if isinstance(color, int):
        return {0: "B", 1: "V", 2: "P"}.get(color)
    if isinstance(color, str):
        c = color.lower()
        if c in ("red", "v", "vermelho"):
            return "V"
        if c in ("black", "p", "preto"):
            return "P"
        if c in ("white", "b", "branco"):
            return "B"
    if numero == 0:
        return "B"
    return None


def salvar_json(data):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ler_json():
    if not JSON_PATH.exists():
        return []
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_blaze():
    r = requests.get(BLAZE_URL, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else data.get("records", [])


@app.get("/api/resultados/ultimos/{qtd}")
def ultimos_resultados(qtd: int):
    if qtd < 1 or qtd > 200:
        raise HTTPException(400, "qtd deve estar entre 1 e 200")

    now = time.time()

    if now - cache["last_update"] > CACHE_SECONDS:
        try:
            raw = fetch_blaze()
            resultados = []

            for item in raw:
                numero = item.get("roll")
                timestamp = item.get("created_at")
                cor = map_cor(item.get("color"), numero)

                if numero is None or timestamp is None or cor is None:
                    continue

                resultados.append({
                    "numero": int(numero),
                    "timestamp": timestamp,
                    "cor": cor,
                    "fonte": "blaze_api"
                })

            cache["data"] = resultados
            cache["last_update"] = now
            salvar_json(resultados)

        except Exception:
            cache["data"] = ler_json()

    return cache["data"][:qtd]
