from celery import Celery
from celery.schedules import crontab
from app.config import CELERY_BROKER_URL, CELERY_BACKEND_URL

celery_app = Celery(
    "tfg_bateria",
    broker=CELERY_BROKER_URL,
    backend=CELERY_BACKEND_URL,
)

# O puedes autodiscover, pero debes tener __init__.py en todos los submódulos
celery_app.autodiscover_tasks(['app.tasks'])
# Importa explícitamente cualquier módulo que no cumpla el patrón “tasks”
celery_app.conf.imports = (
    "app.tasks.task_event_rules",
)

celery_app.conf.beat_schedule = {
    "evaluar-reglas-eventos": {
        "task": "app.tasks.task_event_rules.evaluate_event_rules",
        "schedule": crontab(minute="*/1"),
    },
}