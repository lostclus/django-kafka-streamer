from kafkastreamer import Streamer, register
from tests.testapp.models import ModelA, ModelB, ModelC


class ModelAStreamer(Streamer):
    topic = "model-a"


register(ModelA, ModelAStreamer)


class ModelBStreamer(Streamer):
    topic = "model-b"
    include = ["z"]

    def load_z(self, obj, batch):
        return obj.x + obj.y

    def get_extra_data(self, obj, batch):
        return {"e": "extra"}


register(ModelB, ModelBStreamer)


class ModelCStreamer(Streamer):
    topic = "model-c"
    include = ["a", "b"]
    select_related = ["a", "b"]


register(ModelC, ModelCStreamer)
