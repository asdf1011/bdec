#!/usr/bin/env python

from setuptools import setup, find_packages

import bdec

long_description = """\
A set of tools for decoding binary files given a specification written in a
flexible xml based syntax. It supports decoding to xml or python objects, and
can generate quality C decoders.
"""

setup(name='bdec',
      version=bdec.__version__,
      description='Generates decoders for binary file formats given a high level specification.',
      long_description=long_description,
      author='Henry Ludemann',
      author_email='misc@hl.id.au',
      url='http://www.hl.id.au/projects/bdec/',
      download_url='http://www.hl.id.au/projects/bdec/files/bdec-%s.tar.gz' % bdec.__version__,
      packages=find_packages(exclude=["specs", "specs.*"]),
      package_data={'bdec': ['templates/c/*']},
      entry_points={'console_scripts': [
          'bcompile = bdec.tools.compile:main',
          'bdecode = bdec.tools.decode:main',
          ]},
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
