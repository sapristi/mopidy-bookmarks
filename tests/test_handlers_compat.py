"""Compat tests for Mopidy 3.x vs 4.x JSON-RPC / WebSocket imports.

RED test: handlers.py must import on both Mopidy 3.4.2
(mopidy.internal.jsonrpc + mopidy.http.handlers) and Mopidy 4.0.4
(mopidy._exts.http.jsonrpc + mopidy._exts.http.handlers).
"""

import json


def test_handlers_importable():
    import mopidy_bookmarks.handlers as h

    assert hasattr(h, "BMWebSocketHandler")
    assert hasattr(h, "make_jsonrpc_wrapper")


def test_make_jsonrpc_wrapper_describe():
    from mopidy_bookmarks import handlers as h
    from mopidy_bookmarks.core import BMCore

    inspector_methods = [
        "core.resume",
        "core.start_sync",
        "core.stop_sync",
        "core.get_current_bookmark",
        "core.store.get",
        "core.store.set",
        "core.store.delete",
    ]

    # Use dummy actors (proxies are unwrapped via pykka Future handling,
    # but plain objects work for describe + direct calls).
    class DummyBMCore:
        def resume(self, uri):
            return True

        def start_sync(self, uri):
            return True

        def stop_sync(self):
            return None

        def get_current_bookmark(self):
            return None

    class DummyStore:
        def get(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            return None

        def delete(self, *args, **kwargs):
            return None

    wrapper = h.make_jsonrpc_wrapper(DummyBMCore(), DummyStore(), BMCore)
    assert hasattr(wrapper, "handle_json")

    # core.describe must be exposed and list our methods
    response_raw = wrapper.handle_json(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "core.describe"})
    )
    assert response_raw is not None
    # handle_json returns bytes on Mopidy 4, str on Mopidy 3
    if isinstance(response_raw, bytes):
        response_raw = response_raw.decode()
    response = json.loads(response_raw)
    assert "result" in response
    for method in inspector_methods:
        assert method in response["result"], f"{method} missing in describe"


def test_websocket_handler_base():
    import tornado.websocket

    from mopidy_bookmarks import handlers as h

    assert issubclass(h.BMWebSocketHandler, tornado.websocket.WebSocketHandler)
    assert hasattr(h.BMWebSocketHandler, "broadcast")
