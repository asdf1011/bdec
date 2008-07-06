
import unittest

import bdec
from tools.release import get_changelog

class TestRelease(unittest.TestCase):
    def test_changelog(self):
        text = """
Blah blah

Download
========

* `Version 9.9.9`_

   Blah blah:
   * Did this
   * Did that

* `Version %s`_

   This is the current version
   """ % bdec.__version__
        offset, version, changelog = get_changelog(text)
        self.assertEqual('9.9.9', version)
        self.assertEqual('Blah blah:\n* Did this\n* Did that', changelog)

