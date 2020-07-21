import json
from peewee import TextField


class LimitError(Exception):
    pass


class LTextField(TextField):
    def __init__(self, max_length, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length

    def db_value(self, value):
        if value:
            if self.max_length and len(value) > self.max_length:
                raise LimitError(
                    f"sqlite field max length ({self.max_length}) exceeded"
                )
        return value


class JsonField(LTextField):
    def db_value(self, value):
        return super().db_value(json.dumps(value))

    def python_value(self, value):
        return json.loads(value) if value else None
