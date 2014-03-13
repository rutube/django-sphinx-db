# coding: utf-8

from django.test import TestCase
from django.db import models
from django.db.models import Sum
from backend.models import SphinxModel, sphinx_escape

class TagsIndex(SphinxModel):
    """ Модель индекса тегов."""

    class Meta:
        managed = False
        db_table = 'squirrel_tags_idx'

    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)


class VideoIndex(SphinxModel):
    """ Модель индекса видео."""

    class Meta:
        managed = False
        db_table = 'squirrel_video_idx'

    id = models.CharField(max_length=255, db_column='docid', primary_key=True)
    title = models.CharField(max_length=255)


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
        print query
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

    def testCharFieldExcludeInWithoutMatch(self):
        """ MATCH(@field1 value1 @field2 -(value2, value3)) """
        qs = VideoIndex.objects.filter(title=u'Без названия')
        total = qs.count()
        video1 = qs[0]
        video2 = qs[1]
        ids = (video1.id, video2.id)
        excluded = qs.exclude(id__in=ids).count()
        self.assertEqual(total, excluded + 2)

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
                # преобразования к unicode и str работают корректно
                unicode(qs.query)
                str(qs.query)
            except (UnicodeDecodeError, UnicodeEncodeError):
                self.fail('UnicodeDecodeError: %s' % query_text)

    def testCastIntToChar(self):
        """
        делаем запрос с условием по char филду, используя
        числовое значение, не должны получить экспешн
        """

        try:
            TagsIndex.objects.get(name=100500)
        except TagsIndex.DoesNotExist:
            pass
        except AttributeError:
            self.fail('Fail while casting int to char')

    def testAggregateSum(self):
        qs = TagsIndex.objects.match(u'"ТВ"'.encode('utf-8'))

        iter_sum = sum(qs.values_list('id', flat=True))
        aggr_sum = qs.aggregate(Sum('id'))['id__sum']

        self.assertEqual(iter_sum, aggr_sum)
