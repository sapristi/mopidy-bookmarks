import os
import sqlite3
import json
import logging
import functools

import pykka
logger = logging.getLogger(__name__)

class SizeLimitError(Exception):
    pass

class Controller(pykka.ThreadingActor):
    def __init__(self, dbfile, max_keys, max_length, table_name, rows_create_statement):
        super().__init__()
        self.max_keys = max_keys
        self.max_length = max_length
        self.table_name = table_name
        self._conn = None
        self.dbfile = dbfile

        conn = sqlite3.connect(dbfile)
        c = conn.cursor()
        try:
            c.execute(f"CREATE TABLE {table_name} {rows_create_statement}")
            conn.commit()

        except sqlite3.OperationalError as e:
            logger.info("SQL ERROR ? %s", e)
            pass

    def conn(self):
        if self._conn:
            return self._conn

        self._conn = sqlite3.connect(self.dbfile) 
        return self._conn

    def _count_objects(self):
        c = self.conn().cursor()
        c.execute(f"select count(*) from {self.table_name}")
        return c.fetchone()[0]

    def _key_exists(self, key, column):
        c = self.conn().cursor()
        c.execute("select * from ? where ?=?", (key,))
        return len(c.fetchall()) > 0

    def _check_length(self, *args, **kwargs):
        s = f"{args}{kwargs}"
        if len(s) > self.max_length:
            raise SizeLimitError(
                f"Size limit reached ({len(s)} > {self.max_length}) "
                f"[{self.table_name}]",
            )

    def _check_rows_nb_before_insert(self):
        if self._count_objects() >= self.max_keys:
            raise SizeLimitError(
                f"Keys limit reached ({self.max_keys}), cannot save new entry "
                f"[{self.table_name}]",
            )
