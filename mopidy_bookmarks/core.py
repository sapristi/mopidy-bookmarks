import pykka
import logging
import functools
import json
import asyncio
import threading

import tornado.websocket
from mopidy.core import CoreListener, PlaybackController
from mopidy.internal import jsonrpc
# from .handlers import BMWebSocketHandler
from .controllers import BookmarksController
# from . import Extension

# import logger
logger = logging.getLogger(__name__)

main_io_loop = tornado.ioloop.IOLoop.current()

registry = {}

class BMCore(pykka.ThreadingActor):

    def __init__(self, mopidy_core, data_dir):
        super().__init__()
        self.mopidy_core = mopidy_core

        self.bmcontroller_actor = BookmarksController.start(
            data_dir / "bookmark.sqlite3",
            100,
            10000
        )
        self.controller = self.bmcontroller_actor.proxy()
        self.current_bookmark = None
        self.resuming = False
        self.stop_to_ignore = 0

    def on_stop(self):
        self.bmcontroller_actor.stop()

    def start_syncing(self, bookmark_name):

        def callback():
            self.sync_current_bookmark()
            self.start_syncing()

        self.current_bookmark = bookmark_name

    def sync_current_bookmark(self):
        if not self.current_bookmark:
            return
        current_time = self.mopidy_core.playback.get_time_position().get()
        current_track = self.mopidy_core.tracklist.index().get()
        if current_time is not None and current_track is not None:
            self.controller.update(self.current_bookmark, current_track, current_time)
            return True
        else:
            logger.warning("Cannot sync status: %s %s", current_track, current_time)
            return False

    def create_bookmark(self, bookmark_name):
        """Creates a new bookmark"""
        tltracks = self.mopidy_core.tracklist.get_tl_tracks().get()
        tracks = [tlt.track for tlt in tltracks]
        track_uris = [t.uri for t in tracks]
        logger.info("Creating bookmark %s from %s", bookmark_name, track_uris)
        self.controller.save(bookmark_name, track_uris)
        self.start_syncing(bookmark_name)
        self.sync_current_bookmark()

    def resume_bookmark(self, bookmark_name):
        """Resumes playback from a bookmark."""
        self.resuming = True
        self.mopidy_core.tracklist.clear()
        bookmark_data = self.controller.load(bookmark_name).get()
        logger.info('Resuming %s', bookmark_name)
        if (bookmark_data["tracks"] is None or
            bookmark_data["current_track"] is None or
            bookmark_data["current_time"] is None):
            logger.warning("Cannot resume bookmark %s", bookmark_data)
            return False
        track_uris = json.loads(bookmark_data["tracks"])
        tltracks = self.mopidy_core.tracklist.add(uris=track_uris).get()
        current_tlid = tltracks[bookmark_data["current_track"]].tlid
        self.mopidy_core.playback.play(tlid=current_tlid).get()
        self.mopidy_core.playback.set_state("playing")
        self.mopidy_core.playback.seek(time_position=bookmark_data["current_time"]).get()
        self.start_syncing(bookmark_name)
        self.resuming = False
        logger.info("Resumed %s", bookmark_name)
        self.stop_to_ignore = 2
        return True

    def stop_sync(self):
        """Stop syncing the current bookmark."""
        logger.info("stop sync %s %s", self.current_bookmark, self.stop_to_ignore)
        if self.stop_to_ignore:
            self.stop_to_ignore -= 1
            return
        self.sync_current_bookmark()
        self.current_bookmark = None

        event = {"event": "sync_stop"}
        registry["BMWebSocketHandler"].broadcast(event, registry.get("io_loop"))
        return True

    def get_sync_status(self):
        return {
            "current_bookmark": self.current_bookmark
        }

    def tick(self):
        logger.info("Ticking, syncing")
        self.sync_current_bookmark()


class MopidyCoreListener(pykka.ThreadingActor, CoreListener):
    def __init__(self, config, core):
        super().__init__()
        self.core = core
        self.data_dir = registry["Extension"].get_data_dir(config)
        logger.info('INIT CORE LISTENER(%s) %s',  core, self.data_dir)

    def on_start(self):
        self.bmcore = BMCore.start(self.core, self.data_dir)
        self.timer = PeriodicTimer.start(3, [self.bmcore])
        self.timer.proxy().start_ticking()
        registry["bmcore"] = self.bmcore
        logger.info("START CORE LISTENER; %s", self.bmcore)

    def on_stop(self):
        logger.info('STOPPING')
        self.bmcore.stop()
        self.timer.stop()

    def tracklist_changed(self):
        logger.info('tracklist changed')
        self.bmcore.proxy().stop_sync()

    def playback_state_changed(self, old_state, new_state):
        logger.info("new state: %s -> %s", old_state, new_state)


class PeriodicTimer(pykka.ThreadingActor):
    def __init__(self, period, to_notify):
        super().__init__()
        self.period = period
        self.stop_pending = False
        self.to_notify = to_notify

    def start_ticking(self):
        self._periodic()

    def stop_ticking(self):
        self.stop_pending = True

    def on_stop(self):
        self.stop_ticking()

    def _periodic(self):
        if self.stop_pending:
            return

        for actor in self.to_notify:
            actor.proxy().tick()

        threading.Timer(self.period, self._periodic).start()
