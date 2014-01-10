# coding: utf-8

from django.test import TestCase
from django.db import models
from backend.models import SphinxModel, sphinx_escape

class TagsIndex(SphinxModel):
    """ Модель индекса тегов."""

    class Meta:
        managed = False
        db_table = 'squirrel_tags_idx'

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


class BackendTestCase(TestCase):

    def _fixture_setup(self):
        """ Нет БД - нет фикстур."""
        pass

    def _fixture_teardown(self):
        """ Нет БД - нет фикстур."""
        pass

    def setUp(self):
        super(BackendTestCase, self).setUp()
        self.escaped_match = r"MATCH('\^abc')"
        self.query = "^abc"

    def assertQueryExecuted(self, qs, substr=None):
        query = str(qs.query)
        list(qs)
        substr = substr or self.escaped_match
        if type(substr) is unicode:
            substr = substr.encode('utf-8')
        self.assertIn(substr, query)

    def testMatchEscaping(self):
        qs = TagsIndex.objects.match(sphinx_escape(self.query))
        self.assertQueryExecuted(qs)

    def testAndNodeWithMatch(self):
        qs = TagsIndex.objects.match(sphinx_escape(self.query)).filter(id__gt=2)
        self.assertQueryExecuted(qs)

    def testNotEqual(self):
        qs = TagsIndex.objects.match(sphinx_escape(self.query)).notequal(id=4)
        self.assertQueryExecuted(qs)

    def testFieldExactLookup(self):
        qs = TagsIndex.objects.filter(name__exact=u"Котики")
        self.assertQueryExecuted(qs, substr=u'@name ("Котики")')

    def testFieldNoUnicodeLookup(self):
        qs = TagsIndex.objects.filter(name__exact="Котики")
        self.assertQueryExecuted(qs, substr=u'@name ("Котики")')

    def testCharFieldIn(self):
        qs = TagsIndex.objects.filter(
            name__in=(u"Шедевры рекламы", u"Новость дня"), id__gt=44)
        self.assertQueryExecuted(qs, u"Шедевры рекламы")

    def testCharFieldExcludeIn(self):
        qs = TagsIndex.objects.exclude(
            name__in=(u"Шедевры рекламы", u"Новость дня")).match(name=u"или")
        self.assertQueryExecuted(qs, u"Шедевры рекламы")

    def testCharFieldExcludeOne(self):
        qs = TagsIndex.objects.exclude(
            name=u"Новость дня").match(u"и")
        self.assertQueryExecuted(qs, u"Новость дня")

    def testIntFieldExcludeOne(self):
        qs = TagsIndex.objects.exclude(id=44)
        self.assertQueryExecuted(qs, u"id <> 44")

    def testIntFieldExcludeList(self):
        qs = TagsIndex.objects.exclude(id__in=(44, 66))
        self.assertQueryExecuted(qs, u"id NOT IN")

    def testRepresentQuery(self):
        for query_text in (
            u'тест',
            'тест',
            'test тест',
            u'test тест',
            '\xd1\x82\xd0\xb5\xd1\x81\xd1\x82',
            '\u0442\u0435\u0441\u0442',
            u'\u0442\u0435\u0441\u0442'
        ):
            qs = TagsIndex.objects.filter(name__exact=query_text)
            try:
                # эквивалент: u"%s" % query_text
                unicode(qs.query)
            except UnicodeDecodeError:
                self.fail('UnicodeDecodeError: %s' % query_text)
