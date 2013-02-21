# coding: utf-8

from django.test import TestCase
from django.db import models
from backend.models import SphinxModel, sphinx_escape

class TagsIndex(SphinxModel):
    """ Модель индекса тегов."""

    class Meta:
        managed = False
        db_table = 'squirell_tags_idx'

    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)


from django.test.simple import DjangoTestSuiteRunner


class SphinxSearchTestRunner(DjangoTestSuiteRunner):
    '''TestRunner с отключенным созданием и удалением БД.'''

    def setup_databases(self, *args, **kwargs):
        '''Настраивает БД перед запуском тестов.'''
        return ([],[])

    def teardown_databases(self, *args, **kwargs):
        '''Откатывает БД после выполнения тестов.'''
        pass


class SimpleTest(TestCase):

    def _fixture_setup(self):
        """ Нет БД - нет фикстур."""
        pass

    def _fixture_teardown(self):
        """ Нет БД - нет фикстур."""
        pass

    def testEscaping(self):
        qs = TagsIndex.objects.match(sphinx_escape('~'))
        result = list(qs)
        query, params = qs.query.sql_with_params()
        self.assertIn("MATCH('\\\\~')", query)