import logging
from mopidy import models

logger = logging.getLogger(__name__)


def name_from_uri(uri):
    try:
        return uri.split("bookmark:")[1]
    except IndexError:
        logger.warning("Bad bookmark uri: %s", uri)
        return None


def bookmark_to_model(bookmark):
    track_models = [models.Track(**track) for track in bookmark.tracks]

    return models.Playlist(
        uri=f"bookmark:{bookmark.name}",
        name=bookmark.name,
        tracks=list(track_models),
        last_modified=bookmark.last_modified,
    )
