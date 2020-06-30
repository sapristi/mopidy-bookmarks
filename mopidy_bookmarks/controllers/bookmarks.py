import os
import sqlite3
import json
import logging
import functools

from .base import Controller

logger = logging.getLogger(__name__)

class BookmarksController(Controller):
    def __init__(self, dbfile, max_bookmarks, max_length):
        super().__init__(
            dbfile, max_bookmarks, max_length, "bookmark",
            """(
            name text,
            current_track int,
            current_time int,
            tracks text
            )""")

    def _bookmark_exists(self, name):
        c = self.conn().cursor()
        c.execute("select * from bookmark where name=?", (name,))
        return len(c.fetchall()) > 0

    def save(self, name, track_uris):
        logger.info("Saving bookmark %s", name)
        uris_str = json.dumps(track_uris)
        self._check_length(name, uris_str)
        c = self.conn().cursor()
        if self._bookmark_exists(name):
            c.execute("""update bookmark
            set tracks=?
            where name=?""",
            (uris_str, name))
        else:
            self._check_rows_nb_before_insert()
            c.execute("""insert into bookmark
            (name, tracks) values (?, ?)""",
            (name, uris_str))
        self.conn().commit()

    def update(self, name, current_track, current_time):
        c = self.conn().cursor()
        logger.info("Updating bookmark %s with %s, %s", name, current_track, current_time)
        c.execute("""update bookmark
        set current_track=?, current_time=?
        where name=?""",
        (current_track, current_time, name))
        self.conn().commit()

    def delete(self, name):
        c = self.conn().cursor()
        c.execute("""delete from bookmark where name=?""", (name,))
        self.conn().commit()

    def load(self, name):
        c = self.conn().cursor()
        c.execute("select * from bookmark where name=?", (name,))
        row = c.fetchone()
        return {
            "name": row[0],
            "current_track": row[1],
            "current_time": row[2],
            "tracks": row[3]
        }
