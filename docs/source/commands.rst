.. _commands:

Commands
========

There is ``manage.py kafkastreamer_refresh`` command to force full refresh of
registered models.

Options
-------

``--source SOURCE``
    Set the ``source`` context value.

``--model app.model``
    Set filter by model. By default stream all registered models.

``--no-async``
    No asynchronous run, e.g execute in foreground without Celery task. By
    default execution is asynchronous in background using Celery task.
