import time

import mock
import pykka

import mopidy_bookmarks
import mopidy

from .dummy_backend import DummyBackend
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


config = {
    'core': {
        "data_dir": "tests/data",
        "max_tracklist_length": 100,
    },
    'http': {
        'hostname': '127.0.0.1',
        'port': '6680'
    },
    'bookmarks': {
        'enabled': True,
        'sync_period': 500,
        'max_bookmarks': 10,
        'max_bookmark_length': 1000,
    }
}


def test_bmcore():
    tracks = [mopidy.models.Track(uri=f"dummy:test{i}", length=1000) for i in range(5)]

    bmbackend = mopidy_bookmarks.backend.BookmarksBackend.start(
        config = config, audio = None
    ).proxy()
    dbackend = DummyBackend.start(config=config, audio=None).proxy()
    mopidy_core = mopidy.core.Core.start(
        config, backends=[bmbackend, dbackend]).proxy()

    core_listener = mopidy_bookmarks.MopidyCoreListener.start(
        config,
        mopidy_core,
    ).proxy()
    time.sleep(1)

    bmcore = core_listener.bmcore.get()

    bm = mopidy_core.playlists.create("testbm", "bookmark:").get()
    bm_bis = mopidy.models.Playlist(uri=bm.uri, name=bm.name, tracks=tracks)
    mopidy_core.playlists.save(bm_bis).get()

    pls = mopidy_core.playlists.as_list().get()

    mopidy_core.tracklist.add(uris=[t.uri for t in tracks]).get()
    mopidy_core.playback.play()

    mopidy_core.playback.next().get()
    mopidy_core.playback.seek(100).get()
    mopidy_core.playback.play()
    assert bmcore.get_current_bookmark().get() == None

    bmcore.start_sync(uri=bm.uri).get()
    assert bmcore.get_current_bookmark().get().uri == bm.uri

    current_track = mopidy_core.playback.get_current_track().get()
    current_seek = mopidy_core.playback.get_time_position().get()
    logger.info("CURRENT TRACK %s", current_track)

    time.sleep(1)
    mopidy_core.tracklist.clear().get()
    bmcore.resume(uri=bm.uri).get()

    time.sleep(1)
    current_track = mopidy_core.playback.get_current_track().get()
    logger.info("CURRENT TRACK %s", current_track)

    assert current_track == mopidy_core.playback.get_current_track().get()
    assert current_seek == mopidy_core.playback.get_time_position().get()

    core_listener.stop()
    mopidy_core.stop()
    bmbackend.stop()
    dbackend.stop()
