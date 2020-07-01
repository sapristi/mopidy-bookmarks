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
            "core.create_bookmark": bmcore.BMCore.create_bookmark,
            "core.resume_bookmark": bmcore.BMCore.resume_bookmark,
            "core.sync_current_bookmark": bmcore.BMCore.sync_current_bookmark,
            "core.stop_sync": bmcore.BMCore.stop_sync,
            "core.get_sync_status": bmcore.BMCore.get_sync_status,
        }
    )
    return jsonrpc.JsonRpcWrapper(
        objects={
            "core.create_bookmark": bmcore_actor.create_bookmark,
            "core.resume_bookmark": bmcore_actor.resume_bookmark,
            "core.sync_current_bookmark": bmcore_actor.sync_current_bookmark,
            "core.stop_sync": bmcore_actor.stop_sync,
            "core.get_sync_status": bmcore_actor.get_sync_status,
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
        bmcore.registry.setdefault("io_loop", io_loop)
        logger.info("REGISTRY %s", bmcore.registry)
        self.bmcore = bmcore.registry.get("bmcore")
        logger.info("WS HANDLER: INIT WITH %s; %s", self.bmcore, io_loop)
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

class BMHttpHandler(tornado.web.RequestHandler):
    keys = ["settings"]

    def check_request(self, arg, request):
        return arg in self.keys and len(request.body) < 10000

    def initialize(self, data_dir, allowed_origins):
        self.data_dir = data_dir
        self.allowed_origins = allowed_origins

    def get(self, arg):
        self.set_header("Access-Control-Allow-Origin", "*")
        res = store.load(self.data_dir, arg)
        self.write(res)

    def post(self, arg):
        self.set_header("Access-Control-Allow-Origin", "*")
        req = self.request
        if check_request(arg, req):
            store.save(self.data_dir, "settings", req.body)


