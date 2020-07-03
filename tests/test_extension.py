import mock

from mopidy_bookmarks import Extension, core as bmcore
import mopidy

def test_get_default_config():
    ext = Extension()

    config = ext.get_default_config()

    assert "[bookmarks]" in config
    assert "enabled = true" in config
    assert "sync_period = 500" in config
    assert "max_bookmarks = 100" in config
    assert "max_bookmark_length = 100000" in config

def test_get_config_schema():
    ext = Extension()

    schema = ext.get_config_schema()

    # TODO Test the content of your config schema
    assert "sync_period" in schema
    assert "max_bookmarks" in schema
    assert "max_bookmark_length" in schema


# TODO Write more tests

def test_setup():
    registry = mock.Mock()

    ext = Extension()
    ext.setup(registry)
    calls = [mock.call('frontend', bmcore.MopidyCoreListener)]
    registry.add.assert_has_calls(calls, any_order=True)

config = {
    'core': {
        "data_dir": "tests/data"
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
    ext = Extension()

    core = mopidy.core.Core.start(
        config, backends=[]).proxy()

    coreListener = bmcore.MopidyCoreListener.start(config, core)

    coreListener.stop()
    core.stop()
