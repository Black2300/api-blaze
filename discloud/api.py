from fastapi import FastAPI, HTTPException
import requests
import time

app = FastAPI()

BLAZE_URL = "https://blaze.bet.br/api/singleplayer-originals/originals/roulette_games/recent/1"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://blaze.bet.br/pt/games/double",
}

cache = {"raw": [], "last_update": 0.0}
CACHE_SECONDS = 5


def map_cor(color_value, roll_value=None) -> str | None:
    """
    Mapeia o campo 'color' da Blaze para:
    V = vermelho, P = preto, B = branco
    """
    # Caso venha número (padrão da Blaze)
    if isinstance(color_value, int):
        return {0: "B", 1: "V", 2: "P"}.get(color_value)

    # Caso venha string
    if isinstance(color_value, str):
        c = color_value.strip().lower()
        if c in ("red", "r", "v", "vermelho"):
            return "V"
        if c in ("black", "b", "p", "preto"):
            return "P"
        if c in ("white", "w", "branco"):
            return "B"

    # Fallback: se o número for 0, normalmente é branco
    if roll_value == 0:
        return "B"

    return None


def fetch_blaze_raw():
    r = requests.get(BLAZE_URL, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and data.get("records"):
        return data["records"]
    return []


@app.get("/api/resultados/ultimos/{qtd}")
def ultimos_resultados(qtd: int):
    if qtd <= 0 or qtd > 200:
        raise HTTPException(status_code=400, detail="qtd deve estar entre 1 e 200")

    now = time.time()

    # Atualiza cache
    if now - cache["last_update"] > CACHE_SECONDS:
        try:
            cache["raw"] = fetch_blaze_raw()
            cache["last_update"] = now
        except requests.RequestException as e:
            if not cache["raw"]:
                raise HTTPException(status_code=502, detail=f"Falha ao consultar Blaze: {str(e)}")

    resultados = []
    for item in cache["raw"]:
        numero = item.get("roll") if item.get("roll") is not None else item.get("numero")
        timestamp = item.get("created_at") or item.get("timestamp")
        cor = map_cor(item.get("color") if item.get("color") is not None else item.get("cor"), numero)

        # Remove registros inválidos (evita null)
        if numero is None or timestamp is None or cor is None:
            continue

        resultados.append(
            {
                "numero": int(numero),
                "timestamp": timestamp,
                "cor": cor,
                "fonte": "blaze_api",
            }
        )

        if len(resultados) >= qtd:
            break

    return resultados