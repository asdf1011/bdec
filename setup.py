#!/usr/bin/env python

from setuptools import setup, find_packages

import bdec

long_description = """\
Write specifications for existing binary formats in a flexible xml based
syntax, and have decoders automatically generated for you. Written in Python,
it currently supports native decoding to xml or python objects, as well as
generating quality C decoders.
"""

version=bdec.__version__

setup(name='bdec',
      version=version,
      description='Generates decoders for binary file formats given a high level specification.',
      long_description=long_description,
      author='Henry Ludemann',
      author_email='misc@hl.id.au',
      url='http://www.hl.id.au/Projects/bdec/',
      download_url='http://www.hl.id.au/Projects/bdec/files/bdec-%s.tar.gz' % version,
      packages=find_packages(exclude=["specs", "specs.*"]),
      package_data={'bdec': ['templates/c/*']},
      install_requires=['pyparsing', 'nose', 'mako'],
      zip_safe=True,
      license="GNU LGPL",
      test_suite='nose.collector',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Utilities',
          ],
     )
