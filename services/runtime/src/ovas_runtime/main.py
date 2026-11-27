from fastapi import FastAPI

from ovas_runtime import __version__

app = FastAPI(title="Open Voice Agent Studio runtime", version=__version__)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}
