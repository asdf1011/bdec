"""
A script for testing all of the example specifications.

It attempts to load each example specification, and will attempt to decode all
of the supplied sample files.
"""
import glob
import os.path
import unittest

import bdec.spec.xmlspec as spec

class BaseTest:
    def test_spec_load(self):
        spec.load(self.filename)

def _create_tests():
    """
    Return a list of testcase objects for each of the example specification files.
    """
    path = os.path.join(os.path.dirname(__file__), '..')
    result = {}
    for filename in glob.glob(os.path.join(path, '*.xml')):
        name = os.path.splitext(os.path.split(filename)[1])[0]
        testname = "Test%s%s" % (name[0].upper(), name[1:])

        result[name] = type(testname, (unittest.TestCase, BaseTest), dict(filename=filename))
    assert result, "No example specifications found!"
    return result

globals().update(_create_tests())
