import pykka
import logging

from mopidy import backend
from mopidy import models
from .utils import name_from_uri, bookmark_to_model

logger = logging.getLogger(__name__)


class BookmarksPlaylistProvider(backend.PlaylistsProvider):
    def __init__(self, backend, config):
        super().__init__(backend)
        self._bmcore = None
        self._bmcontroller = None

    @property
    def bmcore(self):
        if not self._bmcore:
            self._bmcore = pykka.ActorRegistry.get_by_class_name("BMCore")[
                0
            ].proxy()
        return self._bmcore

    @property
    def bmcontroller(self):
        if not self._bmcontroller:
            self._bmcontroller = pykka.ActorRegistry.get_by_class_name(
                "BookmarksController"
            )[0].proxy()
        return self._bmcontroller

    def get_items(self, uri):
        tracks = self.bmcontroller.get_items(name_from_uri(uri)).get()
        return [
            models.Ref.track(name=track["name"], uri=track["uri"])
            for track in tracks
        ]

    def as_list(self):
        bookmark_names = self.bmcontroller.as_list().get()
        return [
            models.Ref.playlist(name=name, uri=f"bookmark:{name}")
            for name in bookmark_names
        ]

    def delete(self, uri):
        """Deletes the given bookmark"""
        name = name_from_uri(uri)
        if name == self.bmcore.current_bookmark.get():
            self.bmcore.stop_sync()
        res = self.bmcontroller.delete(name).get()
        return res

    def lookup(self, uri):
        bookmark = self.bmcontroller.get(self.name_from_uri(uri))
        if bookmark is None:
            return None
        return bookmark.to_mopidy_model()

    def refresh(self):
        pass

    def create(self, name):
        if name == self.bmcore.current_bookmark:
            self.bmcore.stop_sync()
        bookmark = self.bmcontroller.save(name, []).get()
        return bookmark_to_model(bookmark)

    def save(self, playlist):
        if playlist.name == self.bmcore.current_bookmark:
            self.bmcore.stop_sync()
        tracks = [
            {"name": tr.name, "uri": tr.uri, "length": tr.length}
            for tr in playlist.tracks
        ]
        bookmark = self.bmcontroller.save(playlist.name, tracks).get()
        return bookmark_to_model(bookmark)


class BookmarksBackend(pykka.ThreadingActor, backend.Backend):
    uri_schemes = ["bookmark"]

    def __init__(self, config, audio):
        super().__init__()
        self.audio = audio
        self.playlists = BookmarksPlaylistProvider(self, config)
        self.playback = backend.PlaybackProvider(audio=audio, backend=self)
