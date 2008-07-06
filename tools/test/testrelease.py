
import os.path
import unittest

import bdec
from tools.release import get_changelog, notify

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

    def test_notify(self):
        commands = []
        def mock_system(command):
            commands.append(command)
            return 0
        message = 'I am a change\n\nwith several lines'
        notify('9.9.9', message, 7, mock_system)
        self.assertEqual(2,  len(commands))
        command = commands[0][:commands[0].index(' ')]
        args = commands[0][len(command):].strip()
        expected = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'website', 'website.integ', 'build', 'freshmeat-submit-1.6', "freshmeat-submit")
        self.assertEqual(os.path.normpath(expected), os.path.normpath(command))
        self.assertEqual('-n --project bdec --version 9.9.9 --changes "%s" --release-focus "7" --gzipped-tar-url http://www.hl.id.au/projects/bdec/files/bdec-9.9.9.tar.gz' % message, args)

        self.assertEqual('./setup.py register', commands[1])
