"""A dummy backend for use in tests.

This backend implements the backend API in the simplest way possible.  It is
used in tests of the frontends.
"""


import pykka
import logging
from mopidy import backend
from mopidy.models import Ref, SearchResult

logger = logging.getLogger(__name__)


class DummyBackend(pykka.ThreadingActor, backend.Backend):
    def __init__(self, config, audio, library_tracks):
        super().__init__()

        self.library = DummyLibraryProvider(
            library_tracks=library_tracks, backend=self
        )
        if audio:
            self.playback = backend.PlaybackProvider(audio=audio, backend=self)
        else:
            self.playback = DummyPlaybackProvider(audio=audio, backend=self)

        self.uri_schemes = ["dummy"]


class DummyLibraryProvider(backend.LibraryProvider):
    root_directory = Ref.directory(uri="dummy:/", name="dummy")

    def __init__(self, library_tracks, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dummy_library = library_tracks
        self.dummy_get_distinct_result = {}
        self.dummy_browse_result = {}
        self.dummy_find_exact_result = SearchResult()
        self.dummy_search_result = SearchResult()

    def browse(self, path):
        return self.dummy_browse_result.get(path, [])

    def get_distinct(self, field, query=None):
        return self.dummy_get_distinct_result.get(field, set())

    def lookup(self, uri):
        uri = Ref.track(uri=uri).uri
        return [t for t in self.dummy_library if uri == t.uri]

    def refresh(self, uri=None):
        pass

    def search(self, query=None, uris=None, exact=False):
        if exact:  # TODO: remove uses of dummy_find_exact_result
            return self.dummy_find_exact_result
        return self.dummy_search_result


class DummyPlaybackProvider(backend.PlaybackProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uri = None
        self._time_position = 0

    def pause(self):
        return True

    def play(self):
        return self._uri and self._uri != "dummy:error"

    def change_track(self, track):
        """Pass a track with URI 'dummy:error' to force failure"""
        self._uri = track.uri
        self._time_position = 0
        return True

    def prepare_change(self):
        pass

    def resume(self):
        return True

    def seek(self, time_position):
        self._time_position = time_position
        return True

    def stop(self):
        self._uri = None
        return True

    def get_time_position(self):
        return self._time_position
