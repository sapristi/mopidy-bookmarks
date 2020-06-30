import pykka
import logging
import functools
import json
import asyncio

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

    def on_stop(self):
        self.bmcontroller_actor.stop()

    def sync_current_bookmark(self):
        if not self.current_bookmark:
            return
        current_time = self.mopidy_core.playback.get_time_position().get()
        current_track = self.mopidy_core.tracklist.index().get()
        if current_time is not None and current_track is not None:
            self.controller.update(self.current_bookmark, current_track, current_time)
            return True
        else:
            return False

    def create_bookmark(self, bookmark_name):
        """Creates a new bookmark"""
        tltracks = self.mopidy_core.tracklist.get_tl_tracks().get()
        tracks = [tlt.track for tlt in tltracks]
        track_uris = [t.uri for t in tracks]
        logger.info("Creating bookmark %s from %s", bookmark_name, track_uris)
        self.controller.save(bookmark_name, track_uris)
        self.current_bookmark = bookmark_name
        self.sync_current_bookmark()

    def resume_bookmark(self, bookmark_name):
        """Resumes playback from a bookmark."""
        self.resuming = True
        self.mopidy_core.tracklist.clear()
        bookmark_data = self.controller.load(bookmark_name).get()
        logger.info('Resuming %s', bookmark_data)
        if (bookmark_data["tracks"] is None or
            bookmark_data["current_track"] is None or
            bookmark_data["current_time"] is None):
            return False
        track_uris = json.loads(bookmark_data["tracks"])
        tltracks = self.mopidy_core.tracklist.add(uris=track_uris).get()
        logger.info("Resumed %s", tltracks)
        current_tlid = tltracks[bookmark_data["current_track"]].tlid
        self.mopidy_core.playback.play(tlid=current_tlid).get()
        self.mopidy_core.playback.set_state("playing")
        self.mopidy_core.playback.seek(time_position=bookmark_data["current_time"]).get()
        self.resuming = False

    def stop_sync(self):
        """Stop syncing the current bookmark."""
        if not self.current_bookmark:
            logger.info("Stop sync: no current bookmark")
            return
        if self.resuming:
            logger.info("Stop sync: currently resuming bookmark")
            return
        logger.info("stop sync %s", self.current_bookmark)
        self.sync_current_bookmark()

        event = {"event": "sync_stop"}
        registry["BMWebSocketHandler"].broadcast(event, registry.get("io_loop"))
        logger.info("Current time is %s", current_time)



class MopidyCoreListener(pykka.ThreadingActor, CoreListener):
    def __init__(self, config, core):
        super().__init__()
        self.core = core
        self.data_dir = registry["Extension"].get_data_dir(config)
        logger.info('INIT CORE LISTENER(%s) %s',  core, self.data_dir)

    def on_start(self):
        self.bmcore = BMCore.start(self.core, self.data_dir)
        registry.setdefault("core", self.bmcore)
        logger.info("START CORE LISTENER; %s", self.bmcore)

    def on_stop(self):
        logger.info('STOPPING')
        self.bmcore.stop()

    def tracklist_changed(self):
        logger.info('tracklist changed')
        self.bmcore.proxy().stop_sync()

    def playback_state_changed(self, old_state, new_state):
        logger.info("new state: %s -> %s", old_state, new_state)

