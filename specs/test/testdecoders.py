"""
Unit tests for testing all of the provided specifications.

It attempts to load each example specification, and will attempt to decode all
of the supplied sample files.
"""
from ConfigParser import ConfigParser
import glob
import os.path

from bdec.test.decoders import create_classes

def _create_decode_classes():
    """
    Return a dictionary of testcase objects for each of the example specification files.
    """
    testdir = os.path.dirname(__file__)
    path = os.path.join(testdir, '..')
    result = {}
    config = ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'fixme.cfg'))
    for filename in glob.glob(os.path.join(path, '*.xml')):
        # Create a test class per specification, which each sample file being
        # a test method.
        name = os.path.splitext(os.path.split(filename)[1])[0]

        datadir = os.path.join(testdir, name)
        tests = []
        if os.path.exists(datadir):
            for datafile in os.listdir(datadir):
                tests.append((datafile[:datafile.index('.')], filename,
                    [os.path.join(datadir, datafile)], []))

        result.update(create_classes(name, tests, config))
    assert result, "No example specifications found!"
    return result

globals().update(_create_decode_classes())
