import re
from django.db import models
from django.db.models.sql import Query
from django.db.models.query import QuerySet
from django_sphinx_db.backend.sphinx.compiler import SphinxWhereNode


def sphinx_escape(value):
    if type(value) not in (str, unicode):
        return value
    value = re.sub(r"([=<>\(\)|\-!@~\"&/\\\^\$\=])", r"\\\1", value)
    value = re.sub(r'(SENTENCE|PARAGRAPH)', r"\\\1", value, flags=re.I)
    return value


class SphinxQuery(Query):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('where', SphinxWhereNode)
        super(SphinxQuery, self).__init__(*args, **kwargs)


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

    def filter(self, *args, **kwargs):
        """ String attributes can't be compared with = term, so they are
        replaced with MATCH('@field_name "value"')."""
        match_args = []
        for field_name, value in kwargs.items():
            try:
                if field_name.endswith('__exact'):
                    field_name = field_name[:-7]
                field = self.model._meta.get_field(field_name)
                if isinstance(field, models.CharField):
                    match_args.append(
                        '@%s "%s"' % (field_name, sphinx_escape(value)))
                    del kwargs[field_name]
            except models.FieldDoesNotExist:
                continue
        if match_args:
            match_expression = ' '.join(match_args)
            return self.match(match_expression).filter(*args, **kwargs)
        return super(SphinxQuerySet, self).filter(*args, **kwargs)

    def match(self, expression):
        qs = self._clone()
        match = "MATCH(%s)"
        return qs.extra(where=[match], params=[expression])

    def notequal(self, **kw):
        """ Support for <> term, NOT(@id=value) doesn't work."""
        qs = self._clone()
        where = []
        for field_name, value in kw.items():
            field = self.model._meta.get_field(field_name)
            if type(field) is SphinxField:
                col = '@%s' % field.attname
            else:
                col = field.db_column
            value = field.get_prep_value(sphinx_escape(value))
            where.append('%s <> %s' % (col, value))
        return qs.extra(where=where)

    def options(self, **kw):
        """ Setup OPTION clause for query."""
        qs = self._clone()
        qs.query.options = kw
        return qs

    def group_by(self, *args):
        qs = self._clone()
        qs.query.group_by = qs.query.group_by or []
        qs.query.group_by.extend([a for a in args
                                  if a not in qs.query.group_by])
        return qs

    def _clone(self, klass=None, setup=False, **kwargs):
        """ Add support of cloning self.query.options."""
        result = super(SphinxQuerySet, self)._clone(klass, setup, **kwargs)
        options = getattr(self.query, 'options', None)
        if options:
            result.query.options = options
        return result


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

    def group_by(self, *args):
        return self.get_query_set().group_by(*args)


class SphinxField(models.TextField):
    pass

class SphinxModel(models.Model):
    class Meta:
        abstract = True

    objects = SphinxManager()
