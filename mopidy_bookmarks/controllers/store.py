import os
import logging

from peewee import (
    Model, Field,
    SqliteDatabase,
    TextField, IntegerField,
    DoesNotExist
)

from .generic import LTextField, JsonField, LimitError

logger = logging.getLogger(__name__)


class StoreController:
    def __init__(self, dbfile, max_items, max_length):

        db = SqliteDatabase(dbfile)
        class Store(Model):
            key = LTextField(primary_key=True, max_length=100)
            value = JsonField(max_length=max_length)

            class Meta:
                database = db

        self.Store = Store
        self.max_keys = max_keys
        db.create_tables([self.Store])

    def save(self, key, value):
        item, created = self.Store.get_or_create(key=key)
        if (created and
            self.max_items and
            self.Store.select().count() > self.max_items
        ):
            raise LimitError(f"Maximum number of items ({self.max_items}) reached.")
        item.value = value
        item.save()

    def load(self, key):
        try:
            return self.Store[key]
        except DoesNotExist:
            return None

    def delete(self, key):
        item = self.Store[key]
        item.delete_instance()
