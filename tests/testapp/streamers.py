from kafkastreamer import Streamer, register
from tests.testapp.models import ModelA, ModelB, ModelC, ModelD, ModelE, ModelF, ModelG


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


@register(ModelD)
class ModelDStreamer(Streamer):
    topic = "model-d"
    include = ["f", "e_set"]
    select_related = ["f"]
    prefetch_related = ["e_set"]
    handle_related = ["f", "e_set"]


@register(ModelE)
class ModelEStreamer(Streamer):
    topic = "model-e"
    include = ["d"]
    select_related = ["d"]
    handle_related = ["d"]


@register(ModelF)
class ModelFStreamer(Streamer):
    topic = "model-f"
    include = ["d"]
    select_related = ["d"]
    handle_related = ["d"]


@register(ModelG)
class ModelGStreamer(Streamer):
    topic = "model-g"
    include = ["d_set"]
    prefetch_related = ["d_set"]
    handle_related = ["d_set"]
