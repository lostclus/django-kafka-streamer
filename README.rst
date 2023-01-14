django-kafka-streamer
=====================

.. image:: https://github.com/lostclus/django-kafka-streamer/actions/workflows/tests.yml/badge.svg
    :target: https://github.com/lostclus/django-kafka-streamer/actions

.. image:: https://img.shields.io/pypi/v/django-kafka-streamer.svg
    :target: https://pypi.org/project/django-kafka-streamer/
    :alt: Current version on PyPi

.. image:: https://img.shields.io/pypi/pyversions/django-kafka-streamer
    :alt: PyPI - Python Version

.. image:: https://img.shields.io/pypi/djversions/django-kafka-streamer
    :alt: PyPI - Django Version

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
