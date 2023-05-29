from kafkastreamer import Streamer, register
from tests.testapp.models import ModelA, ModelB, ModelC


@register(ModelA)
class ModelAStreamer(Streamer):
    topic = "model-a"


@register(ModelB)
class ModelBStreamer(Streamer):
    topic = "model-b"
    include = ["z"]

    def load_z(self, obj, batch):
        return obj.x + obj.y

    def get_extra_data(self, obj, batch):
        return {"e": "extra"}


class ModelCStreamer(Streamer):
    topic = "model-c"
    include = ["a", "b"]
    select_related = ["a", "b"]


# use register as plain function call
register(ModelC, ModelCStreamer)
