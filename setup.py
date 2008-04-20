#!/usr/bin/env python

from setuptools import setup, find_packages

import bdec

long_description = """\
Write specifications for existing binary formats in a flexible xml based
syntax, and have decoders automatically generated for you. Written in Python,
it currently supports decoding to xml or python objects.
"""

version=bdec.__version__

setup(name='bdec',
      version=version,
      description='bdec binary decoder',
      long_description=long_description,
      author='Henry Ludemann',
      author_email='misc@hl.id.au',
      url='http://www.hl.id.au/Projects/bdec/',
      download_url='http://www.hl.id.au/Projects/bdec/files/bdec-%s.tar.gz' % version,
      packages=find_packages(exclude=["specs", "specs.*"]),
      install_requires=['pyparsing'],
      license="BSD",
      test_suite='nose.collector',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Utilities',
          ],
     )
