import os
import logging
import pykka

from peewee import (
    Model, Field,
    SqliteDatabase,
    TextField, IntegerField,
)

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
            track_uris = JsonField(max_length=max_length, null=True)

            class Meta:
                database = self.db

        self.Bookmark = Bookmark
        self.max_bookmarks = max_bookmarks
        self.dbfile = dbfile

    def on_start(self):
        self.db.init(self.dbfile)
        self.db.create_tables([self.Bookmark])

    def on_stop(self):
        self.db.close()

    def save(self, name, track_uris):
        bookmark, created = self.Bookmark.get_or_create(name=name)
        if (created and
            self.max_bookmarks and
            self.Bookmark.select().count() > self.max_bookmarks
        ):
            raise LimitError(f"Maximum number of bookmarks ({self.max_bookmarks}) reached.")
        bookmark.track_uris = track_uris
        bookmark.current_track = None
        bookmark.current_time = None
        bookmark.save()

    def update(self, name, current_track, current_time):
        bookmark = self.Bookmark[name]
        bookmark.current_track=current_track
        bookmark.current_time=current_time
        bookmark.save()

    def delete(self, name):
        bookmark = self.Bookmark[name]
        bookmark.delete_instance()

    def load(self, name):
        return self.Bookmark[name]

    def list(self):
        return list(self.Bookmark.select().dicts())
