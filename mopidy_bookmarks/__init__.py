import logging
import pathlib
import json
import pkg_resources
import tornado

from mopidy import config, ext

from . import handlers
from . import core

__version__ = pkg_resources.get_distribution("Mopidy-Mowecl").version

logger = logging.getLogger(__name__)


class Extension(ext.Extension):

    dist_name = "Mopidy-Bookmarks"
    ext_name = "bookmarks"
    version = __version__

    def get_default_config(self):
        return config.read(pathlib.Path(__file__).parent / "ext.conf")

    def get_config_schema(self):
        schema = super().get_config_schema()
        return schema

    def setup(self, registry):
        core.registry["BMWebSocketHandler"] = handlers.BMWebSocketHandler
        core.registry["Extension"] = self
        registry.add("frontend", core.MopidyCoreListener)
        registry.add(
            "http:app", {
                "name": self.ext_name,
                "factory": self.http_app_factory}
        )

    def http_app_factory(self, config, core):
        allowed_origins = {
            x.lower() for x in config["http"]["allowed_origins"] if x
        }

        return [
            # (
            #     r"/api/(.*)",
            #     handlers.BMHttpHandler,
            #     {"data_dir": self.get_data_dir(config),
            #      "allowed_origins": allowed_origins}
            # ),
            (
                r"/ws/?", handlers.BMWebSocketHandler, {
                    "core": core,
                    "allowed_origins": "*",
                    "csrf_protection": False
                }
            )
        ]

