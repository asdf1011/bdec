#!/usr/bin/env python

from distutils.core import setup

long_description = """\
Write specifications for existing binary formats in a flexible xml based
syntax, and have decoders automatically generated for you. Written in Python,
it currently supports decoding to xml or python objects.
"""

setup(name='bdec',
      version='0.1.0',
      description='bdec binary decoder',
      long_description=long_description,
      author='Henry Ludemann',
      author_email='misc@hl.id.au',
      url='http://www.hl.id.au/Projects/bdec/',
      packages=['bdec'],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License (revised)',
          'Operating System :: OS Independant',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Utilities',
          ],
     )
