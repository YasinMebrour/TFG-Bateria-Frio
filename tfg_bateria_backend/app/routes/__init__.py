"""Colección de routers de la API."""

from .authentication_routes import router as auth
from .pre_saving_band_routes import router as pre_saving_band
from .saving_config_routes import router as saving_config
from .consumption_routes import router as consumption
from .event_stream_routes import router as event_stream
from .available_dates_routes import router as available_dates
from .influxdb_routes import router as influxdb
from .planning_routes import router as planning
from .tariff_routes import router as tariffs
from .user_routes import router as users
from .event_rule_routes import router as event_rules
from .planning_ws_routes import router as ws_planning

__all__ = [
    "auth",
    "pre_saving_band",
    "saving_config",
    "consumption",
    "event_stream",
    "available_dates",
    "influxdb",
    "planning",
    "tariffs",
    "users",
    "event_rules",
    "ws_planning",
]
