import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host="localhost",
        port=5672,
        credentials=pika.PlainCredentials(
            "saas_user",
            "saas_password",
        ),
    )
)

channel = connection.channel()

channel.queue_declare(queue="test_queue")

message = "Hello from producer!"

channel.basic_publish(
    exchange="",
    routing_key="test_queue",
    body=message,
)

print(f"Sent: {message}")

connection.close()