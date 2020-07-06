import pykka
import logging
import functools
import json
import asyncio
import threading
from playhouse.shortcuts import model_to_dict

import tornado.websocket
from mopidy.internal import jsonrpc

from .handlers import BMWebSocketHandler
from .controllers import BookmarksController

logger = logging.getLogger(__name__)


class BMCore(pykka.ThreadingActor):

    def __init__(self, mopidy_core, config, data_dir):
        super().__init__()
        self.mopidy_core = mopidy_core

        self.bmcontroller_actor = BookmarksController.start(
            data_dir / "bookmark.sqlite3",
            config["bookmarks"]["max_bookmarks"],
            config["bookmarks"]["max_bookmark_length"]
        )
        self.controller = self.bmcontroller_actor.proxy()
        self.current_bookmark = None
        self.resuming = False
        self.stop_to_ignore = 0

    def on_stop(self):
        self.bmcontroller_actor.stop()

    def start_syncing(self, bookmark_name):
        self.current_bookmark = bookmark_name
        self.sync_current_bookmark()

    def sync_current_bookmark(self):
        if not self.current_bookmark:
            return
        current_time = self.mopidy_core.playback.get_time_position().get()
        current_track = self.mopidy_core.tracklist.index().get()
        if current_time is not None and current_track is not None:
            self.controller.update(self.current_bookmark, current_track, current_time)
            return True
        else:
            logger.debug("Cannot sync status: %s %s", current_track, current_time)
            return False

    def create(self, name):
        """Creates a new bookmark"""
        tltracks = self.mopidy_core.tracklist.get_tl_tracks().get()
        tracks = [tlt.track for tlt in tltracks]
        tracks_dict = [{"uri": t.uri, "name": t.name, "length": t.length} for t in tracks]
        logger.debug("Creating bookmark %s from %s", name, tracks_dict)
        self.controller.save(name, tracks_dict)
        self.start_syncing(name)

    def resume(self, name):
        """Resumes playback from a bookmark."""
        self.resuming = True
        self.mopidy_core.tracklist.clear()
        bookmark = self.controller.load(name).get()

        logger.debug('Resuming %s', name)

        bookmark_uris = [t["uri"] for t in bookmark_uris.tracks]
        tltracks = self.mopidy_core.tracklist.add(uris=bookmark_uris).get()
        if bookmark.current_track is not None:
            current_tlid = tltracks[bookmark.current_track].tlid
            self.mopidy_core.playback.play(tlid=current_tlid)
            self.mopidy_core.playback.set_state("playing")

        if bookmark.current_time is not None:
            self.mopidy_core.playback.seek(time_position=bookmark.current_time)

        self.start_syncing(name)
        self.resuming = False
        self.stop_to_ignore = 2
        event = {"event": "sync_start", "bookmark": model_to_dict(bookmark)}
        BMWebSocketHandler.broadcast(event)
        return True

    def stop_sync(self):
        """Stop syncing the current bookmark."""
        if self.stop_to_ignore:
            self.stop_to_ignore -= 1
            return
        self.sync_current_bookmark()
        self.current_bookmark = None

        event = {"event": "sync_stop"}
        BMWebSocketHandler.broadcast(event)
        return True

    def get_sync_status(self):
        """Get the current synced bookmark if any."""
        return {
            "current_bookmark": self.current_bookmark
        }

    def list(self):
        """List saved bookmarks."""
        return {
            "bookmarks": self.controller.list().get()
        }


class PeriodicTimer(pykka.ThreadingActor):
    def __init__(self, period, callback):
        super().__init__()
        self.period = period / 1000.
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
