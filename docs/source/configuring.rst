.. _configuring:

Configuring Django settings
===========================

Ensure that ``kafkastreamer`` present in the ``INSTALLED_APPS`` list in the
project `settings.py`::

    INSTALLED_APPS = [
        ...
        "kafkastreamer",
    ]

The django-kafka-streamer is configured by ``KAFKA_STREAMER`` settings variable
which contains such default values::

    KAFKA_STREAMER = {
        "BOOTSTRAP_SERVERS": None,
        "PRODUCER_OPTIONS": {},
        "BATCH_SIZE": 500,
        "DEFAULT_SOURCE": None,
        "DEFAULT_MESSAGE_SERIALIZER": (
            "kafkastreamer.serializers.flat_json_message_serializer"
        ),
        "DEFAULT_PARTITION_KEY_SERIALIZER": None,
        "DEFAULT_PARTITIONER": None,
    }

Configuration settings
----------------------

``BOOTSTRAP_SERVERS``
    List of Kafka services in `"host:port"` format. For example ``["localhost:9092"]``.

``PRODUCER_OPTIONS``
    Dictionary of additional options passed to the ``KafkaProducer`` constructor.

``BATCH_SIZE``
    Number of records in batch.

``DEFAULT_SOURCE``
    Value to identify source of data. For example ``"mydjangoapp"``.

``DEFAULT_MESSAGE_SERIALIZER``
    Path to serializer function in format ``"package.module.function"``. The
    ``kafkastreamer.serializers`` module has one serializer function
    ``flat_json_message_serializer`` that used by default. This serializer use
    model fields names as is, and ``_`` prefixed fields for meta data and
    context extra fields.

``DEFAULT_PARTITION_KEY_SERIALIZER``
    Path to partition key serializer function. If value ``None`` is set (by
    default) then no partition key will be assigned to messages when streaming.
    The ``kafkastreamer.serializers`` module has one partition key serializer
    function ``object_id_key_serializer`` that use string representation of
    object ID as partition key.

``DEFAULT_PARTITIONER``
    Path to partitioner function. If value ``None`` is set (by default) then no
    partitioner will be applied. The ``kafkastreamer.partitioners`` module has
    one partitioner function ``modulo_partitioner`` that can by used in
    combination with ``object_id_key_serializer`` partition key serializer. The
    ``modulo_partitioner`` will distribute messages over partitions based on
    object ID using formula ``object_id % number_of_partitions``.

For details about bootstrap servers, serializers and partitioners see
`KafkaProducer documentation
<https://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html>`_.
