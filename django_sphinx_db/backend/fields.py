# coding: utf-8

from django.db import models
from datetime import datetime
from time import mktime


class UnixTimestampField(models.IntegerField):
    """UnixTimestampField: creates a DateTimeField that is represented on the
    database as a TIMESTAMP field rather than the usual DATETIME field.
    """

    __metaclass__ = models.SubfieldBase

    def __init__(self, null=False, blank=False, **kwargs):
        super(UnixTimestampField, self).__init__(**kwargs)
        # default for TIMESTAMP is NOT NULL unlike most fields, so we have to
        # cheat a little:
        self.blank, self.isnull = blank, null
        # To prevent the framework from shoving in "not null".
        self.null = True

    def to_python(self, value):
        if isinstance(value, datetime):
            return value

        if value is None:
            return None

        return datetime.fromtimestamp(value)

    def get_prep_value(self, value):
        if isinstance(value, (int, long)):
            return super(UnixTimestampField, self).get_prep_value(value)

        return int(mktime(value.timetuple()))

    def _get_val_from_obj(self, obj):
        value = super(UnixTimestampField, self)._get_val_from_obj(obj)
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromtimestamp(float(value))
        except TypeError:
            return datetime.strptime("%Y-%m-%d %H:%M:%S", value)

    def get_db_prep_value(self, value, *args, **kwargs):
        if value is None:
            return None
        if isinstance(value, (int, long)):
            return value
        return int(mktime(value.timetuple()))
