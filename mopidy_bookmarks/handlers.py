import tornado.websocket
import tornado.ioloop
import tornado.escape
import tornado.web
import logging
import functools

from mopidy.internal import jsonrpc
from . import core as bmcore

from mopidy.http.handlers import WebSocketHandler as MopidyWebSocketHandler, _send_broadcast
logger = logging.getLogger(__name__)

def make_jsonrpc_wrapper(bmcore_actor):
    inspector = jsonrpc.JsonRpcInspector(
        objects={
            "core.create": bmcore.BMCore.create,
            "core.resume": bmcore.BMCore.resume,
            "core.stop_sync": bmcore.BMCore.stop_sync,
            "core.get_sync_status": bmcore.BMCore.get_sync_status,
            "core.list": bmcore.BMCore.list,
        }
    )
    return jsonrpc.JsonRpcWrapper(
        objects={
            "core.create": bmcore_actor.create,
            "core.resume": bmcore_actor.resume,
            "core.stop_sync": bmcore_actor.stop_sync,
            "core.get_sync_status": bmcore_actor.get_sync_status,
            "core.list": bmcore_actor.list,
            "core.describe": inspector.describe,
        },
        decoders=[lambda x: x],
        encoders=[lambda x: x],
    )


# Copy of mopidy WebSocketHandler to avoid clients collision
class BMWebSocketHandler(MopidyWebSocketHandler):

    # XXX This set is shared by all WebSocketHandler objects. This isn't
    # optimal, but there's currently no use case for having more than one of
    # these anyway.
    bmclients = set()

    @classmethod
    def broadcast(cls, msg, io_loop):
        # This can be called from outside the Tornado ioloop, so we need to
        # safely cross the thread boundary by adding a callback to the loop.
        for client in cls.bmclients:
            # One callback per client to keep time we hold up the loop short
            io_loop.add_callback(
                functools.partial(_send_broadcast, client, msg)
            )

    def initialize(self, core, allowed_origins, csrf_protection):
        # tornado ioloop from the HttpServer thread of mopidy
        io_loop = tornado.ioloop.IOLoop.current()
        bmcore.registry.io_loop = io_loop
        self.bmcore = bmcore.registry.bmcore
        self.jsonrpc = make_jsonrpc_wrapper(self.bmcore.proxy())
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

