from mopidy_bookmarks.controllers.bookmarks import BookmarksController
from mopidy_bookmarks.controllers.generic import LimitError

tl1 = ["uri1", "uri2"]
tl2 = ["uri3", "uri2"]
tl3 = ["uri3", "uri2"]*100


def test_controller_simple():

    controller = BookmarksController(":memory:", 3, 100)

    controller.save("test1", tl1)
    controller.update("test1", 1, 10)

    bms = controller.list()
    assert len(bms) == 1

    bm = bms[0]
    assert (bm.name == "test1" and
            bm.track_uris == tl1 and
            bm.current_track == 1 and
            bm.current_time == 10)

    controller.save("test1", tl2)

    bm = controller.load("test1")
    assert (bm.name == "test1" and
            bm.track_uris == tl2 and
            bm.current_track == None and
            bm.current_time == None)

    controller.delete("test1")
    assert len(controller.list()) == 0

def test_controller_limits():

    controller = BookmarksController(":memory:", 3, 20)

    try:
        controller.save("t"*101, tl1)
        assert False
    except LimitError:
        assert True

    try:
        controller.save("test1", tl3)
        assert False
    except LimitError:
        assert True

    controller.save("test1", tl1)
    controller.save("test2", tl1)
    controller.save("test3", tl1)
    try:
        controller.save("test4", tl1)
        assert False
    except LimitError:
        assert True

