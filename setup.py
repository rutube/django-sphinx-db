from distutils.core import setup

setup(
    name='django-sphinx-db',
    version='1.2.0',
    packages=[
        "django_sphinx_db",
        "django_sphinx_db.backend",
        "django_sphinx_db.backend.sphinx",
        "django_sphinx_db.management",
        "django_sphinx_db.management.commands",
    ],
    url='http://github.com/rutube/django-sphinx-db/',
    license='MIT',
    author='Ben Timby',
    author_email='btimby@gmail.com',
    description='Django database backend for SphinxQL.',
    maintainer='Tumbler',
    maintainer_email='stikhonov@rutube.ru',
)
