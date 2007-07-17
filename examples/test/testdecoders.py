"""
A script for testing all of the example specifications.

It attempts to load each example specification, and will attempt to decode all
of the supplied sample files.
"""
import glob
import os.path
import unittest

import bdec.data as dt
import bdec.spec.xmlspec as spec

class _BaseTest:
    def _load_spec(self):
        if not hasattr(self, '_spec'):
            type(self)._spec = spec.load(self.filename)[0]

    def test_spec_load(self):
        self._load_spec()
        self.assertTrue(self._spec is not None)

    def _decode(self, filename):
        self._load_spec()
        datafile = open(filename, 'rb')
        data = dt.Data(datafile.read())
        datafile.close()
        entries = list(self._spec.decode(data))
        self.assertTrue(len(entries) > 0)

def _create_tests():
    """
    Return a list of testcase objects for each of the example specification files.
    """
    testdir = os.path.dirname(__file__)
    path = os.path.join(testdir, '..')
    result = {}
    for filename in glob.glob(os.path.join(path, '*.xml')):
        name = os.path.splitext(os.path.split(filename)[1])[0]
        testcasename = "Test%s%s" % (name[0].upper(), name[1:])

        members = dict(filename=filename)
        datadir = os.path.join(testdir, name)
        if os.path.exists(datadir):
            for datafile in os.listdir(datadir):
                testname = "test_%s" % os.path.splitext(datafile)[0]
                datafile = os.path.join(datadir, datafile)
                method = lambda self:self._decode(datafile)
                method.__name__ = testname
                members[testname] = method
        result[testcasename] = type(testcasename, (unittest.TestCase, _BaseTest), members)
    assert result, "No example specifications found!"
    return result

globals().update(_create_tests())
