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


def callback(ch, method, properties, body):
    print(f"Received: {body.decode()}")


channel.basic_consume(
    queue="test_queue",
    on_message_callback=callback,
    auto_ack=True,
)

print("Waiting for messages...")

channel.start_consuming()