django-kafka-streamer
=====================

.. image:: https://github.com/lostclus/django-kafka-streamer/actions/workflows/tests.yml/badge.svg
    :target: https://github.com/lostclus/django-kafka-streamer/actions

.. image:: https://img.shields.io/pypi/v/django-kafka-streamer.svg
    :target: https://pypi.org/project/django-kafka-streamer/
    :alt: Current version on PyPi

.. image:: https://readthedocs.org/projects/django-kafka-streamer/badge/?version=latest
    :target: http://django-kafka-streamer.readthedocs.io/
    :alt: Documentation

.. image:: https://img.shields.io/pypi/pyversions/django-kafka-streamer
    :alt: PyPI - Python Version

.. image:: https://img.shields.io/pypi/djversions/django-kafka-streamer
    :alt: PyPI - Django Version

.. image:: https://img.shields.io/badge/Published%20on-Django%20Packages-0c3c26
    :target: https://djangopackages.org/packages/p/django-kafka-streamer/
    :alt: Published on Django Packages

django-kafka-streamer is a Django application and library for streaming data to
Apache Kafka.

Features:

* Setup signal handlers to ORM models to transparently send create/update/delete
  events to Kafka
* Handle database object relations
* Celery task to stream large amount of data in background

Links:

* GitHub: https://github.com/lostclus/django-kafka-streamer/
* PyPI: https://pypi.org/project/django-kafka-streamer/
* Documentation: http://django-kafka-streamer.readthedocs.io/
* Consumer library: https://github.com/lostclus/aiosafeconsumer
* Example application: https://github.com/lostclus/WeatherApp

Usage:

`yourapp/models.py`::

    from django.db import models

    class MyModel(models.Model):
        field1 = models.IntegerField()
        field2 = models.CharField(max_length=10)

`yourapp/stramers.py`::

    from kafkastreamer import Streamer, register
    from .models import MyModel

    @register(MyModel)
    class MyModelStreamer(Streamer):
        topic = "model-a"

`yourproject/settings.py`::

    INSTALLED_APPS = [
        ...
        "kafkastreamer",
    ]

    KAFKA_STREAMER = {
        "BOOTSTRAP_SERVERS": ["localhost:9092"],
    },

Any changes in ``MyModel`` data will be automatically streamed to Kafka. To
force stream all data in all registered models type::

    python manage.py kafkastreamer_refresh
