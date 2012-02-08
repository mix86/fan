# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(name='fan',
    version='0.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    package_data={'': ['settings/*']},
    author='Mikhail Petrov',
    author_email='mixael@yandex-team.ru',
    zip_safe=False,
)

