import pykka
import logging
import threading

from mopidy import models

from .handlers import BMWebSocketHandler
from .utils import name_from_uri

logger = logging.getLogger(__name__)


class BMCore(pykka.ThreadingActor):
    def __init__(self, mopidy_core, config, bmcontroller):
        super().__init__()
        self.mopidy_core = mopidy_core

        self.controller = bmcontroller
        self.current_bookmark = None
        self.resuming = False
        self.stop_to_ignore = 0

    def on_start(self):
        logger.debug("BMCore started")

    def _start_syncing(self, bookmark_name):
        self.current_bookmark = bookmark_name
        self.sync_current_bookmark()
        event = {"event": "sync_status_update", "bookmark": bookmark_name}
        BMWebSocketHandler.broadcast(event)

    def sync_current_bookmark(self):
        if not self.current_bookmark:
            return
        logger.debug("Syncing bookmark %s", self.current_bookmark)
        current_time = self.mopidy_core.playback.get_time_position().get()
        current_track = self.mopidy_core.tracklist.index().get()

        if current_time is not None and current_track is not None:
            self.controller.update(
                self.current_bookmark, current_track, current_time
            )
            return True
        else:
            logger.warning(
                "Cannot sync status: track=%s, time=%s",
                current_track,
                current_time,
            )
            return False

    def start_sync(self, uri):
        """Starts syncing the given bookmark with the playback state.

        The tracklist must correspond to the tracks of the bookmark.

        Parameters
        ----------
        uri : str
            The uri of the bookmark to resume

        Returns
        -------
        bool
            `True` if syncing started, else `False`
        """
        tltracks = self.mopidy_core.tracklist.get_tl_tracks().get()
        track_uris = [tlt.track.uri for tlt in tltracks]
        bookmark = self.controller.get(name_from_uri(uri)).get()
        if bookmark is None:
            return False
        bookmark_uris = [t["uri"] for t in bookmark.tracks]
        if bookmark_uris == track_uris:
            self._start_syncing(name_from_uri(uri))
            return True
        else:
            logger.warning(
                "Cannot sync bookmark %s;"
                "tracklist and bookmark tracks are not the same"
            )
            return False

    def resume(self, uri):
        """Resumes playback from a bookmark.

        Populates the tracklist with the tracks of the bookmark, resumes playback from
        the saved position and sync the bookmark with the current playback state (track and time).

        Parameters
        ----------
        uri : str
            The uri of the bookmark to resume

        Returns
        -------
        bool
            `True` if a bookmark was found for the given uri, else `False`
        """
        name = name_from_uri(uri)
        bookmark = self.controller.get(name).get()
        if bookmark is None:
            logger.warning("Cannot find bookmark %s", uri)
            return False

        logger.debug("Resuming bookmark %s", uri)
        self.resuming = True
        self.mopidy_core.tracklist.clear()
        bookmark_uris = [t["uri"] for t in bookmark.tracks]
        tltracks = self.mopidy_core.tracklist.add(uris=bookmark_uris).get()
        if bookmark.current_track is not None:
            current_tlid = tltracks[bookmark.current_track].tlid
            logger.info(f"RESUMING PLAYBACK FROM {current_tlid} now")
            self.mopidy_core.playback.play(tlid=current_tlid).get()
            logger.info("Resumed track %s", tltracks[bookmark.current_track])

            current_t = self.mopidy_core.playback.get_current_track().get()
            state = self.mopidy_core.playback.get_state().get()
            logger.info("State %s; %s", current_t, state)

        if bookmark.current_time is not None:
            self.mopidy_core.playback.seek(
                time_position=bookmark.current_time
            ).get()
            logger.info("Seeked to %s", bookmark.current_time)

        self._start_syncing(name)
        self.resuming = False
        self.stop_to_ignore = 2
        return True

    def stop_sync(self):
        """Stop syncing the current bookmark."""
        if self.stop_to_ignore:
            self.stop_to_ignore -= 1
            return
        self.current_bookmark = None
        event = {"event": "sync_status_update", "bookmark": None}
        BMWebSocketHandler.broadcast(event)

    def get_current_bookmark(self):
        """Get the current synced bookmark if any.

        Returns
        -------
        mopidy.models.Ref or None
            A ref to the current bookmark if any, else None
        """
        if self.current_bookmark:
            return models.Ref.playlist(
                name=self.current_bookmark,
                uri=f"bookmark:{self.current_bookmark}",
            )
        else:
            return None


class PeriodicTimer(pykka.ThreadingActor):
    def __init__(self, period, callback):
        super().__init__()
        self.period = period / 1000.0
        self.stop_pending = False
        self.callback = callback

    def start_ticking(self):
        self._periodic()

    def stop_ticking(self):
        self.stop_pending = True

    def on_stop(self):
        self.stop_ticking()

    def _periodic(self):
        if self.stop_pending:
            return

        self.callback()
        threading.Timer(self.period, self._periodic).start()
