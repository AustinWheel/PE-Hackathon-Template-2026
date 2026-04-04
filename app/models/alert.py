from peewee import CharField, DateTimeField, TextField

from app.database import BaseModel


class Alert(BaseModel):
    alert_name = CharField()
    severity = CharField(default="warning")
    status = CharField(default="firing")  # firing, acknowledged, resolved
    summary = TextField(default="")
    source = CharField(default="")
    notes = TextField(default="")
    fired_at = DateTimeField()
    acknowledged_at = DateTimeField(null=True)
    resolved_at = DateTimeField(null=True)
    acknowledged_by = CharField(null=True)
