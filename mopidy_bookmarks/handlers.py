import tornado.websocket
import tornado.ioloop
import tornado.escape
import tornado.web
import logging
import functools
import pykka

from mopidy.internal import jsonrpc
from mopidy import models


from mopidy.http.handlers import WebSocketHandler as MopidyWebSocketHandler, _send_broadcast
logger = logging.getLogger(__name__)

def make_jsonrpc_wrapper(bmcore_actor, BMCore):
    inspector = jsonrpc.JsonRpcInspector(
        objects={
            "core.create_from_tracklist": BMCore.create_from_tracklist,
            "core.resume": BMCore.resume,
            "core.stop_sync": BMCore.stop_sync,
            "core.get_sync_status": BMCore.get_sync_status,
            "core.get_items": BMCore.get_items,
            "core.as_list": BMCore.as_list,
        }
    )
    return jsonrpc.JsonRpcWrapper(
        objects={
            "core.create_from_tracklist": bmcore_actor.create_from_tracklist,
            "core.resume": bmcore_actor.resume,
            "core.stop_sync": bmcore_actor.stop_sync,
            "core.get_sync_status": bmcore_actor.get_sync_status,
            "core.get_items": bmcore_actor.get_items,
            "core.as_list": bmcore_actor.as_list,
            "core.describe": inspector.describe,
        },

        decoders=[models.model_json_decoder],
        encoders=[models.ModelJSONEncoder],
    )


# Copy of mopidy WebSocketHandler to avoid clients collision
class BMWebSocketHandler(MopidyWebSocketHandler):

    # XXX This set is shared by all WebSocketHandler objects. This isn't
    # optimal, but there's currently no use case for having more than one of
    # these anyway.
    bmclients = set()
    io_loop = None

    @classmethod
    def broadcast(cls, msg):
        # This can be called from outside the Tornado ioloop, so we need to
        # safely cross the thread boundary by adding a callback to the loop.
        for client in cls.bmclients:
            # One callback per client to keep time we hold up the loop short
            cls.io_loop.add_callback(
                functools.partial(_send_broadcast, client, msg)
            )

    def initialize(self, core, BMCore, allowed_origins, csrf_protection):
        # tornado ioloop from the HttpServer thread of mopidy
        BMWebSocketHandler.io_loop = tornado.ioloop.IOLoop.current()
        bmcore_actor = pykka.ActorRegistry.get_by_class_name("BMCore")[0]
        self.jsonrpc = make_jsonrpc_wrapper(bmcore_actor.proxy(), BMCore)
        self.allowed_origins = allowed_origins
        self.csrf_protection = csrf_protection

    def open(self):
        self.set_nodelay(True)
        self.bmclients.add(self)
        logger.debug("New WebSocket connection from %s", self.request.remote_ip)

    def on_close(self):
        self.bmclients.discard(self)
        logger.debug(
            "Closed WebSocket connection from %s", self.request.remote_ip
        )

