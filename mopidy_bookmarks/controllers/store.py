import logging
import pykka

from peewee import Model, SqliteDatabase, DoesNotExist

from playhouse.shortcuts import model_to_dict
from .generic import LTextField, JsonField, LimitError

logger = logging.getLogger(__name__)


class StoreController(pykka.ThreadingActor):
    def __init__(self, dbfile, max_items, max_length):

        super().__init__()
        self.db = SqliteDatabase(None)

        class Store(Model):
            key = LTextField(primary_key=True, max_length=100)
            value = JsonField(max_length=max_length, null=True)

            class Meta:
                database = self.db

        self.Store = Store
        self.max_items = max_items
        self.dbfile = dbfile

    def on_start(self):
        self.db.init(self.dbfile)
        self.db.create_tables([self.Store])

    def on_stop(self):
        self.db.close()

    def save(self, key, value):
        item, created = self.Store.get_or_create(key=key)
        if (
            created
            and self.max_items
            and self.Store.select().count() > self.max_items
        ):
            raise LimitError(
                f"Maximum number of items ({self.max_items}) reached."
            )
        item.value = value
        item.save()

    def get(self, key):
        try:
            return model_to_dict(self.Store[key])
        except DoesNotExist:
            return None

    def delete(self, key):
        item = self.Store[key]
        item.delete_instance()
