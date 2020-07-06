import pykka
import logging

from mopidy import backend
from mopidy.models import Ref
from .controllers import BookmarksController

logger = logging.getLogger(__name__)

class BookmarksPlaylistProvider(backend.PlaylistsProvider):
    def __init__(self, backend, config):
        super().__init__(backend)
        self._controller = None

    @property
    def controller(self):
        if not self._controller:
            self._controller = pykka.ActorRegistry.get_by_class_name("BookmarksController")[0].proxy()
        return self._controller

    def as_list(self):
        bookmarks = self.controller.list().get()
        return [
            Ref.playlist(name=bm['name'], uri=f"bookmark:{bm['name']}")
            for bm in bookmarks
        ]

    def get_items(self, uri):
        bm = self.controller.get(uri.split("bookmark:")[1]).get()
        return [
            Ref.track(uri=uri) for uri in bm.track_uris
        ]
class BookmarksBackend(pykka.ThreadingActor, backend.Backend):
    uri_schemes = ["bookmark"]

    def __init__(self, config, audio):
        super().__init__()
        self.audio = audio
        self.playlists = BookmarksPlaylistProvider(self, config)
        logger.info("INIT BACKEND %s", self.playlists)
