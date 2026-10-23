from datetime import timezone
from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """SQLite drops timezone metadata; restore UTC before serializing the API."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None
                else value.astimezone(timezone.utc))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None
                else value.astimezone(timezone.utc))
