from django.apps import apps
from django.core.management.base import BaseCommand

from kafkastreamer import full_refresh, set_context
from kafkastreamer.tasks import refresh


class Command(BaseCommand):
    help = "Refresh objects in Kafka stream"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=None,
            help="Set source",
        )
        parser.add_argument(
            "--model",
            metavar="app.model",
            dest="models",
            default=[],
            action="append",
            help="Filter by model",
        )
        parser.add_argument(
            "--no-async",
            dest="no_async",
            action="store_true",
            help="No async run",
        )

    def handle(
        self,
        source=None,
        models=None,
        verbosity=None,
        no_async=False,
        **options,
    ):
        if no_async:
            count = 0
            with set_context(source=source):
                if models:
                    for name in models:
                        model = apps.get_model(name)
                        count += full_refresh(model)
                else:
                    count += full_refresh()

            if verbosity:
                self.stdout.write(
                    self.style.SUCCESS(f"{count} messages was send"),
                )
        else:
            result = refresh.delay(models=models or None, source=source)
            self.stdout.write(
                self.style.SUCCESS(f"Streaming will run in background job {result.id}"),
            )
