import pykka
import logging

from mopidy import backend
from mopidy.models import Ref
from .controllers import BookmarksController

logger = logging.getLogger(__name__)

class BookmarksPlaylistProvider(backend.PlaylistsProvider):
    def __init__(self, backend, config):
        super().__init__(backend)
        self._bmcore = None

    @property
    def bmcore(self):
        if not self._bmcore:
            self._bmcore = pykka.ActorRegistry.get_by_class_name("BMCore")[0].proxy()
        return self._bmcore

    def as_list(self):
        return self.bmcore.as_list().get()

    def get_items(self, uri):
        return self.bmcore.get_items(uri).get()

    def delete(self, uri):
        res =self.bmcore.delete(uri).get()
        logger.info("DELETE: %s", res)
        return res

    def refresh(self):
        pass

class BookmarksBackend(pykka.ThreadingActor, backend.Backend):
    uri_schemes = ["bookmark"]

    def __init__(self, config, audio):
        super().__init__()
        self.audio = audio
        self.playlists = BookmarksPlaylistProvider(self, config)
        logger.info("INIT BACKEND %s", self.playlists)
