"""
Unit tests for testing all of the provided specifications.

It attempts to load each example specification, and will attempt to decode all
of the supplied sample files.
"""
import glob
import os.path
import unittest

import bdec.data as dt
import bdec.output.xmlout as xmlout
import bdec.spec.xmlspec as xmlspec
from bdec.test.decoders import create_decoder_classes 

class _BaseTest(object):
    def _load_spec(self):
        if not hasattr(self, '_spec'):
            spec, common, lookup = xmlspec.load(self.filename)
            type(self)._spec = spec
            type(self)._common = common.values()

    def _decode(self, filename):
        self._load_spec()
        if os.path.splitext(filename)[1] == ".gz":
            # As gzip'ed files seek extremely poorly, we'll read the file completely into memory.
            import gzip
            datafile = gzip.GzipFile(filename, 'rb').read()
        else:
            datafile = open(filename, 'rb')

        (exit_code, xml) = self._decode_file(self._spec, self._common, datafile)
        self.assertEqual(0, exit_code)


def _create_decode_function(name, filename):
    """Create a decode function to decode a given file."""
    result = lambda self: self._decode(filename)
    result.__name__ = name
    return result

def _create_decode_classes():
    """
    Return a dictionary of testcase objects for each of the example specification files.
    """
    testdir = os.path.dirname(__file__)
    path = os.path.join(testdir, '..')
    result = []
    for filename in glob.glob(os.path.join(path, '*.xml')):
        name = os.path.splitext(os.path.split(filename)[1])[0]
        testcasename = "%s%s" % (name[0].upper(), name[1:])

        members = dict(filename=filename)
        datadir = os.path.join(testdir, name)
        if os.path.exists(datadir):
            for datafile in os.listdir(datadir):
                testname = "test_%s" % datafile[:datafile.index('.')]
                datafile = os.path.join(datadir, datafile)
                method = _create_decode_function(testname, datafile)
                members[testname] = method

        if not members:
            # If we don't have any data tests, just attempt to load the specification.
            def test_spec_load(self):
                self._load_spec()
                self.assertTrue(self._spec is not None)
            members['test_spec_load'] = test_spec_load
        members[filename] = filename

        result.append((type(testcasename, (_BaseTest, ), members), testcasename))
    assert result, "No example specifications found!"
    return result

globals().update(create_decoder_classes(_create_decode_classes(), __name__))
