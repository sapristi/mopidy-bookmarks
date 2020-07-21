import time

import mopidy_bookmarks
import mopidy

import logging

logger = logging.getLogger(__name__)


def test_get_default_config():
    ext = mopidy_bookmarks.Extension()

    config = ext.get_default_config()

    assert "[bookmarks]" in config
    assert "enabled = true" in config
    assert "sync_period = 500" in config
    assert "max_bookmarks = 100" in config
    assert "max_bookmark_length = 100000" in config


def test_get_config_schema():
    ext = mopidy_bookmarks.Extension()

    schema = ext.get_config_schema()

    # TODO Test the content of your config schema
    assert "sync_period" in schema
    assert "max_bookmarks" in schema
    assert "max_bookmark_length" in schema


def test_bmcore(setup_actors, tracks):
    actors = setup_actors

    mopidy_core = actors["mopidy_core"]
    core_listener = actors["core_listener"]

    bmcore = core_listener.bmcore.get()

    # create a bookmark
    bm = mopidy_core.playlists.create("testbm", "bookmark:").get()
    bm_bis = mopidy.models.Playlist(uri=bm.uri, name=bm.name, tracks=tracks)
    mopidy_core.playlists.save(bm_bis).get()

    # setup some tracks
    mopidy_core.tracklist.add(uris=[t.uri for t in tracks]).get()
    mopidy_core.playback.play()

    mopidy_core.playback.next().get()
    mopidy_core.playback.seek(100).get()

    # not syncing: default
    assert bmcore.get_current_bookmark().get() is None

    # syncing : save current track/time
    bmcore.start_sync(uri=bm.uri).get()
    assert bmcore.get_current_bookmark().get().uri == bm.uri
    current_track = mopidy_core.playback.get_current_track().get()
    current_seek = mopidy_core.playback.get_time_position().get()

    # Clear the tracklist will stop sync
    mopidy_core.tracklist.clear().get()
    time.sleep(0.5)
    assert bmcore.get_current_bookmark().get() is None

    # Resume: setup tracklist, current track/time and sync status
    bmcore.resume(uri=bm.uri).get()
    assert current_track == mopidy_core.playback.get_current_track().get()
    assert current_seek == mopidy_core.playback.get_time_position().get()
    assert bmcore.get_current_bookmark().get().uri == bm.uri
