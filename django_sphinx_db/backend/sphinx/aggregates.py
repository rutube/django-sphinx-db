# coding: utf-8
from django.db.models.fields import IntegerField, FloatField
from django import VERSION

ordinal_aggregate_field = IntegerField()
computed_aggregate_field = FloatField()

from django.db.models.sql.aggregates import Aggregate as base_aggregate

LESS_DJANGO_16 = VERSION[:2] < (1,6)


class Aggregate(base_aggregate):
    def as_sql(self, qn, connection):
        if hasattr(self.col, 'as_sql'):
            if LESS_DJANGO_16:
                field_name = self.col.as_sql(qn, connection)
            else:
                field_name, params = self.col.as_sql(qn, connection)
        elif isinstance(self.col, (list, tuple)):
            # единственное отличие от базового класса
            # если прилетает tuple с алиасом имени таблицы
            # не учитываем его, а берем только имя филда

            # базовый метод полностью:
            # def as_sql(self, qn, connection):
            #     "Return the aggregate, rendered as SQL."
            #
            #     if hasattr(self.col, 'as_sql'):
            #         field_name = self.col.as_sql(qn, connection)
            #     elif isinstance(self.col, (list, tuple)):
            #         field_name = '.'.join([qn(c) for c in self.col])
            #     else:
            #         field_name = self.col
            #
            #     params = {
            #         'function': self.sql_function,
            #         'field': field_name
            #     }
            #     params.update(self.extra)
            #
            #     return self.sql_template % params

            field_name = self.col[-1]
        else:
            field_name = self.col

        params = {
            'function': self.sql_function,
            'field': field_name
        }
        params.update(self.extra)

        if LESS_DJANGO_16:
            return self.sql_template % params
        else:
            return self.sql_template % params, {}


class Avg(Aggregate):
    is_computed = True
    sql_function = 'AVG'

class Count(Aggregate):
    is_ordinal = True
    sql_function = 'COUNT'
    sql_template = '%(function)s(%(distinct)s%(field)s)'

    def __init__(self, col, distinct=False, **extra):
        super(Count, self).__init__(col, distinct=distinct and 'DISTINCT ' or '', **extra)

class Max(Aggregate):
    sql_function = 'MAX'

class Min(Aggregate):
    sql_function = 'MIN'

class StdDev(Aggregate):
    is_computed = True

    def __init__(self, col, sample=False, **extra):
        super(StdDev, self).__init__(col, **extra)
        self.sql_function = sample and 'STDDEV_SAMP' or 'STDDEV_POP'

class Sum(Aggregate):
    sql_function = 'SUM'

class Variance(Aggregate):
    is_computed = True

    def __init__(self, col, sample=False, **extra):
        super(Variance, self).__init__(col, **extra)
        self.sql_function = sample and 'VAR_SAMP' or 'VAR_POP'
