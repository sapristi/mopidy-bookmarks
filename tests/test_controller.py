from mopidy_bookmarks.controllers.bookmarks import BookmarksController
from mopidy_bookmarks.controllers.generic import LimitError
import logging

logger = logging.getLogger(__name__)
tl1 = ["uri1", "uri2"]
tl2 = ["uri3", "uri2"]
tl3 = ["uri3", "uri2"]*100


def test_controller_simple():

    controller = BookmarksController.start(":memory:", 3, 100).proxy()

    controller.save("test1", tl1).get()
    controller.update("test1", 1, 10).get()

    bms = controller.list().get()
    logger.info('BMS %s', bms)
    assert len(bms) == 1

    bm = bms[0]
    assert (bm["name"] == "test1" and
            bm["track_uris"] == tl1 and
            bm["current_track"] == 1 and
            bm["current_time"] == 10)

    controller.save("test1", tl2).get()

    bm = controller.load("test1").get()
    assert (bm.name == "test1" and
            bm.track_uris == tl2 and
            bm.current_track == None and
            bm.current_time == None)

    controller.delete("test1").get()
    assert len(controller.list().get()) == 0

    controller.stop()

def test_controller_limits():

    controller = BookmarksController.start(":memory:", 3, 20).proxy()

    try:
        controller.save("t"*101, tl1).get()
        assert False
    except LimitError:
        assert True

    try:
        controller.save("test1", tl3).get()
        assert False
    except LimitError:
        assert True

    controller.save("test1", tl1).get()
    controller.save("test2", tl1).get()
    controller.save("test3", tl1).get()
    try:
        controller.save("test4", tl1).get()
        assert False
    except LimitError:
        assert True


    controller.stop()
