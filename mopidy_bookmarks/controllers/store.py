import os
import sqlite3
import json
import logging
import functools

from .base import Controller

logger = logging.getLogger(__name__)


class StoreController(Controller):
    def __init__(self, dbfile, max_keys, max_length):
        super().__init__(dbfile, max_keys, max_length, "store", "(key text, data text)")

    def _key_exists(self, key):
        c = self.conn.cursor()
        c.execute("select * from store where key=?", (key,))
        return len(c.fetchall()) > 0

    def save(self, key, data):
        c = self.conn.cursor()
        self._check_length(key, data)
        if self._key_exists(key):
            c.execute("update store set data=? where key=?",
                    (data, key))
        else:
            self._check_rows_nb_before_insert()
            c.execute("insert into store (key, data) values (?, ?)",
                    (key, data))
        self.conn.commit()

    def load(self, key):
        c = self.conn.cursor()
        c.execute("select data from store where key=?", (key,))
        res = c.fetchone()
        return res[0] if res else b"null"

    def delete(self, key):
        c = self.conn.cursor()
        c.execute("delete * from store where key=?", (key,))
