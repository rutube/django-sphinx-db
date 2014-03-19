A fork of [SmartFile](http://www.smartfile.com) [Django](http://www.djangoproject.com)
backend for [SphinxSearch](http://www.sphinxsearch.com) search engine.

Original README can be found [there](https://github.com/smartfile/django-sphinx-db)

## Faststart

### Install django_sphinx_db:
```python
INSTALLED_APPS += ('django_sphinx_db', )

# This is the name of the sphinx server in DATABASES:
# (needed for database router)
SPHINX_DATABASE_NAME = 'sphinx'

# Define the connection to Sphinx
DATABASES = {
    'default': {
        # Your default database connection goes here...
    },
    SPHINX_DATABASE_NAME:  {
        'ENGINE': 'django_sphinx_db.backend.sphinx',
        # The database name does not matter.
        'NAME': '',
        # There is no user name or password.
        'USER': '',
        'PASSWORD': '',
        # Don't use localhost, this will result in using a UDS instead of TCP...
        'HOST': '127.0.0.1',
        'PORT': '9306',
    },
}

# You need routers to determine correct backend for Sphinx models.
DATABASE_ROUTERS = (
    'django_sphinx_db.routers.SphinxRouter',
)
```

### Add some Sphinx models

```python

class MyIndex(SphinxModel):
    class Meta:
        # This next bit is important, you don't want Django to manage
        # the table for this model.
        managed = False

    name = CharField() # If defined in sphinx.conf, could be searchable too.
    content = SphinxField() # Usefull for autogeneration of sphinx.conf.
    date = models.DateTimeField()
    size = models.IntegerField()
```

### Start fulltext searching your data
```python

MyIndex.objects.match("@name ^start of text and text end$")
MyIndex.objects.filter(name="Document name").exclude(size=3)
MyIndex.objects.filter(name="Document name").sum("size")
```

More usage examples can be found in module django_sphinx_db.tests

## Stability

SphinxSearch has some "features" that may cause application crashes.

First, it sometimes crashes on every query (i.e. in 2.2-beta version) when
it has corrupted index files.
In such case, we can fix it by returning empty queryset for every crashed query.

To enable this workaround, add to `settings.py`:

```python
SPHINX_IMMORTAL = True
```

Again, in `workers=threads` mode at high query rate sphinxsearch rejects
connections, returning 54 socket error.

django_sphinx_db can retry query on certain exception messages listed in `settings.py`:

```python
REPEAT_ON_EXCEPTION_MSGS=['Connection reset by peer']
```

## Development status

This backend is used in high-load production at [rutube.ru](http://rutube.ru) with Django-1.5
and Django-1.6. It is supported as more sphinxsearch-related features are requested
 by our team. But we also respond to bug reports and pull-requests at free time.