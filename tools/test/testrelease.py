
import os.path
import StringIO
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
        connections = []
        class MockConnection:
            def __init__(self, domain):
                connections.append(self)
            def request(self, actual, path, json, headers):
                self.json = json
            def getresponse(self):
                response = StringIO.StringIO()
                response.status = 200
                response.reason = ''
                return response
            def close(self):
                pass

        message = 'I am a change\n\nwith several lines'
        notify('9.9.9', message, lambda:'xxx',MockConnection, mock_system, lambda msg:'y', should_send_email=False, tag_list=lambda a,b:'')
        self.assertEqual(1,  len(connections))
        self.assertEqual('{"release": {"tag_list": "", "version": "9.9.9", ' +
            '"changelog": "I am a change with several lines"}, ' +
            '"auth_code": "xxx"}', connections[0].json)

        self.assertEqual(1, len(commands))
        self.assertEqual('./setup.py register', commands[0])

