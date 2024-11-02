django-kafka-streamer Documentation
===================================

django-kafka-streamer is a `Django`_ application and library for streaming data to
`Apache Kafka`_.

.. _Apache Kafka: https://kafka.apache.org/
.. _Django: https://www.djangoproject.com/

Quick Start
===========

.. code-block:: bash

   $ pip install django-kafka-streamer

Make sure ``kafkastreamer`` in the ``INSTALLED_APPS`` list in project
`settings.py`. (see :ref:`configuring`). Then add kafkastreamer settings::

    KAFKA_STREAMER = {
        "BOOTSTRAP_SERVERS": ["localhost:9092"],
    },

Replace ``localhost:9092`` to actual Kafka host and port. Create `stramers.py`
file in app directory which data needs to stream.

`yourapp/stramers.py`::

    from kafkastreamer import Streamer, register
    from .models import MyModel

    @register(MyModel)
    class MyModelStreamer(Streamer):
        topic = "my-topic"

Replace ``MyModel`` to actual model name. Replace ``my-topic`` to actual Kafka
topic name. Any changes in model data will be automatically streamed to Kafka.
To force stream all data in all registered models type::

    python manage.py kafkastreamer_refresh

Table of Contents
=================

.. toctree::
   :maxdepth: 2

   configuring
   streamers
   API </apidoc/index>
   commands
