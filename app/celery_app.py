import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "amqp://guest:guest@localhost:5672//",
)

celery_app = Celery(
    "saas_platform",
    broker=CELERY_BROKER_URL,
    include=["app.tasks.events"],
)

celery_app.conf.task_default_queue = "celery"