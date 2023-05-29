from pytest_djangoapp import configure_djangoapp_plugin

pytest_plugins = configure_djangoapp_plugin(
    app_name="kafkastreamer",
    settings={
        "KAFKA_STREAMER": {
            "DEFAULT_SOURCE": "test",
            "BOOTSTRAP_SERVERS": [],
        },
    },
    extend_INSTALLED_APPS=[
        "tests.testapp",
    ],
    extend_DATABASES={
        "dummy": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
    },
    admin_contrib=True,
)
