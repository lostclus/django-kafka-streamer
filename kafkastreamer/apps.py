from django.apps import AppConfig


class KafkaStreamerConfig(AppConfig):
    name = "kafkastreamer"
    verbose_name = "Kafka Streamer"

    def ready(self):
        from .registry import autodiscover

        autodiscover()
