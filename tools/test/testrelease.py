
import os.path
import unittest

import bdec
from tools.release import shorten_changelog, get_changelog, notify

class TestRelease(unittest.TestCase):
    def test_changelog(self):
        text = """
Blah blah

Download
========

9.9.9 (blah blah)
-----------------

Blah blah:
* Did this.
* Did that.

Ding dong:
* Went there.
* Came back.

1.2.3 (be bop)
--------------

This is the current version
   """
        changelog = get_changelog(text)
        self.assertEqual(2, len(changelog))
        self.assertEqual('9.9.9', changelog[0][0])
        self.assertEqual('blah blah', changelog[0][1])
        self.assertEqual('Blah blah: Did this. Did that. Ding dong: Went there. Came back.', shorten_changelog(changelog[0][2]))

        self.assertEqual('1.2.3', changelog[1][0])
        self.assertEqual('be bop', changelog[1][1])
        self.assertEqual('This is the current version', shorten_changelog(changelog[1][2]))

    def test_notify(self):
        commands = []
        def mock_system(command):
            commands.append(command)
            return 0
        message = 'I am a change\n\nwith several lines'
        notify('9.9.9', message, lambda: 7, mock_system, lambda msg:'y', should_send_email=False)
        self.assertEqual(2,  len(commands))
        command = commands[0][:commands[0].index(' ')]
        args = commands[0][len(command):].strip()
        expected = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'website', 'website.integ', 'build', 'freshmeat-submit-1.6', "freshmeat-submit")
        self.assertEqual(os.path.normpath(expected), os.path.normpath(command))
        self.assertEqual('-n --project bdec --version 9.9.9 --changes "I am a change with several lines" --release-focus "7" --gzipped-tar-url http://www.hl.id.au/projects/bdec/files/bdec-9.9.9.tar.gz', args)

        self.assertEqual('./setup.py register', commands[1])
