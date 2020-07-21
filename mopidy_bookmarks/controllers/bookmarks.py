import logging
import pykka
import time

from peewee import (
    Model,
    SqliteDatabase,
    IntegerField,
    DoesNotExist,
)
from mopidy import models

from .generic import LTextField, JsonField, LimitError

logger = logging.getLogger(__name__)


class BookmarksController(pykka.ThreadingActor):
    def __init__(self, dbfile, max_bookmarks, max_length):
        super().__init__()
        self.db = SqliteDatabase(None)

        class Bookmark(Model):
            name = LTextField(primary_key=True, max_length=100)
            current_track = IntegerField(null=True)
            current_time = IntegerField(null=True)
            tracks = JsonField(max_length=max_length, null=True)
            last_modified = IntegerField(null=True)

            class Meta:
                database = self.db

            def to_mopidy_model(self):
                track_models = [models.Track(**track) for track in self.tracks]

                return models.Playlist(
                    uri=f"bookmark:{self.name}",
                    name=self.name,
                    tracks=list(track_models),
                    last_modified=self.last_modified,
                )

        self.Bookmark = Bookmark
        self.max_bookmarks = max_bookmarks
        self.dbfile = dbfile

    def on_start(self):
        self.db.init(self.dbfile)
        self.db.create_tables([self.Bookmark])

    def on_stop(self):
        self.db.close()

    def save(self, name, tracks):
        bookmark, created = self.Bookmark.get_or_create(name=name)
        if (
            created
            and self.max_bookmarks
            and self.Bookmark.select().count() > self.max_bookmarks
        ):
            raise LimitError(
                f"Maximum number of bookmarks ({self.max_bookmarks}) reached."
            )
        bookmark.tracks = tracks
        bookmark.current_track = None
        bookmark.current_time = None
        bookmark.last_modified = int(time.time())
        bookmark.save()
        return bookmark

    def update(self, name, current_track, current_time):
        bookmark = self.Bookmark[name]
        bookmark.current_track = current_track
        bookmark.current_time = current_time
        bookmark.save()

    def delete(self, name):
        try:
            bookmark = self.Bookmark[name]
            bookmark.delete_instance()
            return True
        except DoesNotExist:
            return False

    def get(self, name):
        try:
            return self.Bookmark[name]
        except DoesNotExist:
            return None

    def get_items(self, name):
        bm = self.Bookmark[name]
        return bm.tracks

    def as_list(self):
        return [bm.name for bm in self.Bookmark.select()]
