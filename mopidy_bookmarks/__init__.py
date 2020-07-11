import logging
import pathlib
import json
import pkg_resources
import tornado
import pykka

from mopidy import config, ext
from mopidy.core import CoreListener

from . import handlers
from .core import BMCore, PeriodicTimer
from .backend import BookmarksBackend
from .controllers import BookmarksController, StoreController

__version__ = pkg_resources.get_distribution("Mopidy-Bookmarks").version

logger = logging.getLogger(__name__)


class Extension(ext.Extension):

    dist_name = "Mopidy-Bookmarks"
    ext_name = "bookmarks"
    version = __version__

    def get_default_config(self):
        return config.read(pathlib.Path(__file__).parent / "ext.conf")

    def get_config_schema(self):
        schema = super().get_config_schema()
        schema["sync_period"] = config.Integer(minimum=50)

        schema["max_bookmarks"] = config.Integer(minimum=0)
        schema["max_bookmark_length"] = config.Integer(minimum=0)
        return schema

    def setup(self, registry):
        registry.add("frontend", MopidyCoreListener)
        registry.add(
            "http:app", {
                "name": self.ext_name,
                "factory": self.http_app_factory}
        )
        registry.add("backend", BookmarksBackend)

    def http_app_factory(self, config, core):
        allowed_origins = {
            x.lower() for x in config["http"]["allowed_origins"] if x
        }

        return [
            (
                r"/ws/?", handlers.BMWebSocketHandler, {
                    "core": core,
                    "BMCore": BMCore,
                    "allowed_origins": allowed_origins,
                    "csrf_protection": config["http"]["csrf_protection"]
                }
            )
        ]


class MopidyCoreListener(pykka.ThreadingActor, CoreListener):
    def __init__(self, config, core):
        super().__init__()
        self.mopidy_core = core
        self.data_dir = Extension.get_data_dir(config)
        self.config = config

    def on_start(self):

        self.bmcontroller = BookmarksController.start(
            self.data_dir / "bookmark.sqlite3",
            self.config["bookmarks"]["max_bookmarks"],
            self.config["bookmarks"]["max_bookmark_length"]
        )
        self.storecontroller = StoreController.start(
            self.data_dir / "bookmark.sqlite3",
            100,
            1000
        )
        self.bmcore = BMCore.start(
            self.mopidy_core, self.config, self.bmcontroller,
            )
        tick_period = self.config["bookmarks"]["sync_period"]
        self.timer = PeriodicTimer.start(
            tick_period,
            lambda: self.bmcore.proxy().sync_current_bookmark()
        )
        self.timer.proxy().start_ticking()

    def on_stop(self):
        logger.info('STOPPING')
        self.bmcore.stop()
        self.bmcontroller.stop()
        self.storecontroller.stop()
        self.timer.stop()

    def tracklist_changed(self):
        logger.info('tracklist changed')
        self.bmcore.proxy().stop_sync()

    def playback_state_changed(self, old_state, new_state):
        logger.info("new state: %s -> %s", old_state, new_state)
