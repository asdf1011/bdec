#!/usr/bin/env python

from distutils.core import setup

long_description = """\
Write specifications for existing binary formats in a flexible xml based
syntax, and have decoders automatically generated for you. Written in Python,
it currently supports decoding to xml or python objects.
"""

version='0.1.1'

setup(name='bdec',
      version=version,
      description='bdec binary decoder',
      long_description=long_description,
      author='Henry Ludemann',
      author_email='misc@hl.id.au',
      url='http://www.hl.id.au/Projects/bdec/',
      download_url='http://www.hl.id.au/Projects/bdec/files/bdec-0.1.1.tar.gz',
      packages=['bdec'],
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
