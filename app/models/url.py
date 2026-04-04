from peewee import BooleanField, CharField, DateTimeField, ForeignKeyField, TextField

from app.database import BaseModel
from app.models.user import User


class Url(BaseModel):
    user = ForeignKeyField(User, backref="urls")
    short_code = CharField()
    original_url = TextField()
    title = CharField()
    is_active = BooleanField()
    created_at = DateTimeField()
    updated_at = DateTimeField()
