import pytest
import time

import mopidy_bookmarks
import mopidy

from tests.dummy_backend import DummyBackend
from tests.dummy_audio import DummyAudio


@pytest.fixture
def config():
    return {
        "core": {"data_dir": "tests/data", "max_tracklist_length": 100},
        "http": {"hostname": "127.0.0.1", "port": "6680"},
        "bookmarks": {
            "enabled": True,
            "sync_period": 500,
            "max_bookmarks": 10,
            "max_bookmark_length": 1000,
            "max_store_items": 10,
            "max_store_item_length": 1000,
        },
    }


@pytest.fixture
def tracks():
    return [
        mopidy.models.Track(uri=f"dummy:test{i}", length=1000) for i in range(5)
    ]


@pytest.fixture
def setup_actors(config, tracks):
    audio = DummyAudio.start(config=config, mixer=None).proxy()
    bmbackend = mopidy_bookmarks.backend.BookmarksBackend.start(
        config=config, audio=audio
    ).proxy()
    dbackend = DummyBackend.start(
        config=config, audio=audio, library_tracks=tracks
    ).proxy()
    mopidy_core = mopidy.core.Core.start(
        config, backends=[bmbackend, dbackend]
    ).proxy()

    core_listener = mopidy_bookmarks.MopidyCoreListener.start(
        config, mopidy_core,
    ).proxy()

    time.sleep(1)

    yield {
        "bmbackend": bmbackend,
        "mopidy_core": mopidy_core,
        "core_listener": core_listener,
    }

    core_listener.stop()
    mopidy_core.stop()
    bmbackend.stop()
    dbackend.stop()
    audio.stop()
