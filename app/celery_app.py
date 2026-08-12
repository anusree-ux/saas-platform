from celery import Celery

celery_app = Celery(
    "saas_platform",
    broker="amqp://saas_user:saas_password@localhost:5672//",
    include=["app.tasks.events"],
)

celery_app.conf.task_default_queue = "celery"