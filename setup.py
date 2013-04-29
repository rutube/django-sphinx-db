#!/bin/env python

import os
from distutils.core import setup

name = 'django-sphinx-db'
version = '0.1'
release = '17'
versrel = version + '-' + release
readme = os.path.join(os.path.dirname(__file__), 'README.rst')
download_url = 'https://github.com/downloads/rutube/django-sphinx-db' \
                           '/' + name + '-' + versrel + '.tar.gz'
long_description = file(readme).read()

setup(
    name = name,
    version = versrel,
    description = 'Django database backend for SphinxQL.',
    long_description = long_description,
    author = 'Ben Timby',
    author_email = 'btimby@gmail.com',
    maintainer = 'Sergey Tikhonov',
    maintainer_email = 'stikhonov@rutube.ru',
    url = 'http://github.com/rutube/django-sphinx-db/',
    download_url = download_url,
    license = 'MIT',
    packages = [
        "django_sphinx_db",
        "django_sphinx_db.backend",
        "django_sphinx_db.backend.sphinx",
        "django_sphinx_db.management",
        "django_sphinx_db.management.commands",
    ],
    classifiers = (
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Python Modules',
    ),
)
