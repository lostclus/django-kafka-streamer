.. _streamers:

Setup streamers
===============

In order to django-kafka-streamer to know which modules to stream, you need to
create a `streamers.py` file in the app directory and define a streamer class for
each model that needs to be streamed. The minimum configuration is::

    from kafkastreamer import Streamer, register
    from .models import MyModel

    @register(MyModel)
    class MyModelStreamer(Streamer):
        topic = "my-topic"

For example your model definition is::

    class MyModel(models.Model):
        field1 = models.IntegerField()
        field2 = models.CharField(max_length=10)

Then when a new instance of ``MyModel`` is created. The following data will be
send to the ``my-topic`` Kafka topic:

.. code-block:: json

    {
        "_time": "2023-01-01T00:00:00Z",
        "_type": "create",
        "id": 1,
        "field1": 1,
        "field2": "abc"
    }

You can use the ``exclude`` attribute to exclude some fields::

    @register(MyModel)
    class MyModelStreamer(Streamer):
        topic = "my-topic"
        exclude = ["field2"]

Then the output will be:

.. code-block:: json

    {
        "_time": "2023-01-01T00:00:00Z",
        "_type": "create",
        "id": 1,
        "field1": 1
    }

The model can have related fields. For example::

    class OtherModel(models.Model):
        other_field = models.IntegerField()

    class MyModel(models.Model):
        field1 = models.IntegerField()
        field2 = models.CharField(max_length=10)
        other = models.ForeignKey(OtherModel)

To make a related object appear in the output, add it to ``include`` and
``select_related`` lists::

    @register(MyModel)
    class MyModelStreamer(Streamer):
        topic = "my-topic"
        include = ["other"]
        select_related = ["other"]

Then the output will be:

.. code-block:: json

    {
        "_time": "2023-01-01T00:00:00Z",
        "_type": "create",
        "id": 1,
        "field1": 1
        "field2": "abc"
        "other_id": 2,
        "other": {
            "id": 2,
            "other_field": 3,
        }
    }

To re-stream the data when the related object of ``OtherModel`` is changed, add
it to the ``handle_related`` list::

    @register(MyModel)
    class MyModelStreamer(Streamer):
        topic = "my-topic"
        include = ["other"]
        select_related = ["other"]
        handle_related = ["other"]

To add additional fields with constant values, use the ``static_fields`` dictionary::

    @register(MyModel)
    class MyModelStreamer(Streamer):
        topic = "my-topic"
        static_fields = {"model": "MyModel"}

To add additional field with calculated value, define a ``load_<field>`` method,
and add the field to the ``include`` list::

    @register(MyModel)
    class MyModelStreamer(Streamer):
        topic = "my-topic"
        include = ["field1_plus_one"]

        def load_field1_plus_one(self, obj, batch):
            return obj.field1 + 1
