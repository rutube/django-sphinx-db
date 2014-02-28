# coding: utf-8

from MySQLdb import OperationalError
import re
from django.conf import settings
from django.db import models, connections, connection
from django.db.models.sql import Query, AND
from django.db.models.query import QuerySet
from django.utils.log import getLogger
from django_sphinx_db.backend.sphinx.compiler import SphinxWhereNode, SphinxExtraWhere, SphinxQLCompiler
from django_sphinx_db.backend.sphinx import aggregates as sphinx_aggregates

def sphinx_escape(value):
    if type(value) not in (str, unicode):
        return value
    value = re.sub(r"([=<>()|!@~&/^$\-\"\\])", r'\\\1', value)
    value = re.sub(r'(SENTENCE|PARAGRAPH)', r'\\\1', value, flags=re.I)
    return value


def immortal_generator(func):
    def inner(*args, **kwargs):
        try:
            gen = func(*args, **kwargs)
            for v in gen:
                yield v
        except OperationalError as e:
            if getattr(settings, 'SPHINX_IMMORTAL', False):
                logger = getLogger("django.db.backends.sphinx")
                try:
                    query = args[0].query
                except (IndexError, AttributeError):
                    query = "unknown"
                logger.error(u"Sphinx search error at '{}'".format(query),
                             exc_info=True)
                return
            raise
    return inner


class SphinxQuery(Query):
    _clonable = ('options', 'match', 'group_limit', 'group_order_by',
                 'with_meta')

    aggregates_module = sphinx_aggregates

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('where', SphinxWhereNode)
        super(SphinxQuery, self).__init__(*args, **kwargs)

    def clone(self, klass=None, memo=None, **kwargs):
        query = super(SphinxQuery, self).clone(klass=klass, memo=memo, **kwargs)
        for attr_name in self._clonable:
            value = getattr(self, attr_name, None)
            if value:
                setattr(query, attr_name, value)
        return query

    def __str__(self):
        def to_str(text):
            if type(text) is unicode:
                # u'тест' => '\xd1\x82\xd0\xb5\xd1\x81\xd1\x82'
                return text.encode('utf-8')
            else:
                # 'тест' => u'\u0442\u0435\u0441\u0442' => '\xd1\x82\xd0\xb5\xd1\x81\xd1\x82'
                # 'test123' => 'test123'
                return str(text)

        compiler = SphinxQLCompiler(self, connection, None)
        query, params = compiler.as_sql()

        params = tuple(map(lambda p: to_str(p), params))
        return to_str(query % params)

    def __unicode__(self):
        compiler = SphinxQLCompiler(self, connection, None)
        query, params = compiler.as_sql()
        return unicode(query % params)


class SphinxQuerySet(QuerySet):

    def __init__(self, model, **kwargs):
        kwargs.setdefault('query', SphinxQuery(model))
        super(SphinxQuerySet, self).__init__(model, **kwargs)

    def using(self, alias):
        # Ignore the alias. This will allow the Django router to decide
        # what db receives the query. Otherwise, when dealing with related
        # models, Django tries to force all queries to the same database.
        # This is the right thing to do in cases of master/slave or sharding
        # but with Sphinx, we want all related queries to flow to Sphinx,
        # never another configured database.
        return self._clone()

    def with_meta(self):
        """ Allows to execute SHOW META immediately after main query."""
        clone = self._clone()
        setattr(clone.query, 'with_meta', True)
        return clone

    def _negate_expression(self, negate, lookup):
        if isinstance(lookup, (tuple, list)):
            result = []
            for v in lookup:
                result.append(self._negate_expression(negate, v))
            return result
        else:
            if not isinstance(lookup, (str, unicode)):
                lookup = unicode(lookup)

            if not lookup.startswith('"'):
                lookup = '"%s"' % lookup
            if negate:
                lookup = '-%s' % lookup
            return lookup


    def _filter_or_exclude(self, negate, *args, **kwargs):
        """ String attributes can't be compared with = term, so they are
        replaced with MATCH('@field_name "value"')."""
        match_kwargs = {}
        for lookup, value in kwargs.items():
            try:
                tokens = lookup.split('__')
                field_name = tokens[0]
                lookup_type = None
                if len(tokens) == 2:
                    lookup_type = tokens[1]
                elif len(tokens) > 2:
                    raise ValueError("Can't build correct lookup for %s" % lookup)
                if lookup == 'pk':
                    field = self.model._meta.pk
                else:
                    field = self.model._meta.get_field(field_name)
                if isinstance(field, models.CharField):
                    if lookup_type and lookup_type not in ('in', 'exact', 'startswith'):
                        raise ValueError("Can't build correct lookup for %s" % lookup)
                    if lookup_type == 'startswith':
                        value = value + '*'
                    field_name = field.attname
                    match_kwargs.setdefault(field_name, set())
                    sphinx_lookup = sphinx_escape(value)
                    sphinx_expr = self._negate_expression(negate, sphinx_lookup)
                    if isinstance(sphinx_expr, list):
                        match_kwargs[field_name].update(sphinx_expr)
                    else:
                        match_kwargs[field_name].add(sphinx_expr)
                    del kwargs[lookup]
            except models.FieldDoesNotExist:
                continue
        if match_kwargs:
            return self.match(**match_kwargs)._filter_or_exclude(negate, *args, **kwargs)
        return super(SphinxQuerySet, self)._filter_or_exclude(negate, *args, **kwargs)

    def get(self, *args, **kwargs):
        return super(SphinxQuerySet, self).get(*args, **kwargs)

    def match(self, *args, **kwargs):
        """ Enables full-text searching in sphinx (MATCH expression).

        qs.match('sphinx_expression_1', 'sphinx_expression_2')
            compiles to
        MATCH('sphinx_expression_1 sphinx_expression_2)

        qs.match(field1='sphinx_loopup1',field2='sphinx_loopup2')
            compiles to
        MATCH('@field1 sphinx_lookup1 @field2 sphinx_lookup2')
        """
        qs = self._clone()
        if not hasattr(qs.query, 'match'):
            qs.query.match = dict()
        for expression in args:
            qs.query.match.setdefault('*', set())
            if isinstance(expression, (list, tuple)):
                qs.query.match['*'].update(expression)
            else:
                qs.query.match['*'].add(expression)
        for field, expression in kwargs.items():
            qs.query.match.setdefault(field, set())
            if isinstance(expression, (list, tuple, set)):
                qs.query.match[field].update(expression)
            else:
                qs.query.match[field].add(expression)
        return qs

    def notequal(self, **kw):
        """ Support for <> term, NOT(@id=value) doesn't work."""
        qs = self._clone()
        where = []
        for field_name, value in kw.items():
            field = self.model._meta.get_field(field_name)
            if type(field) is SphinxField:
                col = '@%s' % field.attname
            else:
                col = field.db_column or field.attname
            value = field.get_prep_value(sphinx_escape(value))
            where.append('%s <> %s' % (col, value))
        qs.query.where.add(SphinxExtraWhere(where, []), AND)
        return qs

    def options(self, **kw):
        """ Setup OPTION clause for query."""
        qs = self._clone()
        try:
            qs.query.options.update(kw)
        except AttributeError:
            qs.query.options = kw
        return qs

    def group_by(self, *args, **kw):
        """ Adds GROUP BY clause to query.

        *args: field names or aliases to group by
        keyword group_limit: (GROUP <N> BY)
            int, limits number of group member to N
        keyword group_order_by: (WITHIN GROUP ORDER BY)
            string list, sets sort order within group
            in example: group_order_by=('-my_weight', 'title')
        """
        group_limit = kw.get('group_limit', 0)
        group_order_by = kw.get('group_order_by', ())
        qs = self._clone()
        qs.query.group_by = qs.query.group_by or []
        for field_name in args:
            if field_name not in qs.query.extra_select:
                field = self.model._meta.get_field_by_name(field_name)[0]
                qs.query.group_by.append(field.column)
            else:
                qs.query.group_by.append(field_name)
        qs.query.group_limit = group_limit
        qs.query.group_order_by = group_order_by
        return qs

    def _clone(self, klass=None, setup=False, **kwargs):
        """ Add support of cloning self.query.options."""
        result = super(SphinxQuerySet, self)._clone(klass, setup, **kwargs)

        return result

    def _fetch_meta(self):
        c = connections[settings.SPHINX_DATABASE_NAME].cursor()
        try:
            c.execute("SHOW META")
            self.meta = dict([c.fetchone()])
        except UnicodeDecodeError:
            self.meta = {}
        finally:
            c.close()

    @immortal_generator
    def iterator(self):
        for row in super(SphinxQuerySet, self).iterator():
            yield row
        if getattr(self.query, 'with_meta', False):
            self._fetch_meta()


class SphinxManager(models.Manager):
    use_for_related_fields = True

    def get_query_set(self):
        # Determine which fields are sphinx fields (full-text data) and
        # defer loading them. Sphinx won't return them.
        # TODO: we probably need a way to keep these from being loaded
        # later if the attr is accessed.
        sphinx_fields = [field.name for field in self.model._meta.fields
                         if isinstance(field, SphinxField)]
        return SphinxQuerySet(self.model).defer(*sphinx_fields)

    def options(self, **kw):
        return self.get_query_set().options(**kw)

    def match(self, expression):
        return self.get_query_set().match(expression)

    def notequal(self, **kw):
        return self.get_query_set().notequal(**kw)

    def group_by(self, *args, **kw):
        return self.get_query_set().group_by(*args, **kw)

    def get(self, *args, **kw):
        return self.get_query_set().get(*args, **kw)


class SphinxField(models.TextField):
    pass


class SphinxModel(models.Model):
    class Meta:
        abstract = True

    objects = SphinxManager()
