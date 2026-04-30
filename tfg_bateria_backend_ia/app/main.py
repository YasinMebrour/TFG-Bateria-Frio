import logging

# Third‑party
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Local
from .core.lifespan import lifespan

logging.basicConfig(level=logging.INFO)
app = FastAPI(lifespan=lifespan)


# ----------------------
# Middleware
# ----------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Ajusta en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    """Endpoint de prueba para verificar el estado de la API."""
    return {"message": "API Digital Twin Modulo IA - funcionando"}


from app.routes.consumption import router as consumption
app.include_router(consumption)
