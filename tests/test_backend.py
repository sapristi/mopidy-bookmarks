import mopidy

import logging

logger = logging.getLogger(__name__)


def test_backend(setup_actors, tracks):
    actors = setup_actors

    mopidy_core = actors["mopidy_core"]

    bm = mopidy_core.playlists.create("testbm", "bookmark:").get()
    bm_bis = mopidy.models.Playlist(uri=bm.uri, name=bm.name, tracks=tracks)
    mopidy_core.playlists.save(bm_bis).get()

    bms = mopidy_core.playlists.as_list().get()
    assert bms[0].name == "testbm"

    items = mopidy_core.playlists.get_items(uri=bms[0].uri).get()
    assert [item.name for item in items] == [track.name for track in tracks]

    bm_ter = mopidy_core.playlists.lookup(uri=bms[0].uri).get()
    assert bm_ter.tracks == bm_bis.tracks

    mopidy_core.playlists.refresh()
