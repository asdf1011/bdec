#!/usr/bin/env python

from setuptools import setup, find_packages

import bdec

short_description = 'A set of tools for decoding binary files.'
long_description = """\
A set of tools for decoding binary files given a specification written in a
flexible xml based syntax. It supports decoding to xml or python objects, and
can generate quality C decoders.
"""

setup(name='bdec',
      version=bdec.__version__,
      description=short_description,
      long_description=long_description,
      author='Henry Ludemann',
      author_email='henry@protocollogic.com',
      url='http://www.protocollogic.com/',
      download_url='http://www.protocollogic.com/files/bdec-%s.tar.gz' % bdec.__version__,
      packages=find_packages(exclude=["specs", "specs.*", 'tools', 'tools.*',
          'regression', 'regression.*']),
      package_data={'bdec': ['templates/c/*']},
      entry_points={'console_scripts': [
          'bcompile = bdec.tools.compile:main',
          'bdecode = bdec.tools.decode:main',
          'bencode = bdec.tools.encode:main',
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
