
from collections import defaultdict
from ConfigParser import ConfigParser
import glob
import os.path
import re

from bdec.test.decoders import create_classes

def _find_regression_tests(spec_extension, regression_dir):
    # There are four file types in the regression folder.
    #
    #  1. Specifications
    #       <name>.<spec_extension>
    #  2. Data files we should successfully decoded
    #       <name>[-<entry>].<number>.<extension>
    #  3. Expected decoded xml
    #       <name>[-<entry>].<number>.expected.xml
    #  4. Data files that should fail to decode
    #       <name>[-<entry>].failure.<number>.<extension>
    class Test:
        def __init__(self):
            self.filename = None
            self.successes = []
            self.failures = []
        def __str__(self):
            return '%s: successes (%s), failures (%s)' % (self.filename, ','.join(self.successes), ','.join(self.failures))

    tests = defaultdict(Test)
    for filename in os.listdir(regression_dir):
        path = os.path.join(regression_dir, filename)
        if os.path.isfile(path):
            names = filename.split('.')
            if len(names) == 2:
                assert names[1] == spec_extension, \
                    "'%s' looks like specification, but doesn't end with '%s'!" % spec_extension
                tests[names[0]].filename = path
            elif len(names) == 3:
                tests[names[0]].successes.append(path)
            elif len(names) == 4 and names[2] == 'expected':
                # We don't store these explicitly
                pass
            elif len(names) == 4 and names[1] == 'failure':
                tests[names[0]].failures.append(path)
            else:
                assert os.path.splitext(filename) not in ['swp'], \
                        "Unknown regression file '%s'!" % path
    for name, test in tests.items():
        entry = None
        if '-' in name:
            assert test.filename is None
            entry = name.split('-')[0]
            test.filename = os.path.join(regression_dir, entry + '.' + spec_extension)
            assert os.path.exists(test.filename)
        assert test.filename is not None, 'Missing specification for regression %s!' % name
        yield name, test.filename, entry, test.successes, test.failures

def _create_test_cases():
    """Create a set of test cases based for the specs in the regression folder.

    Each folder in the regression directory contains specifications and data
    files to test.

    return -- A dictionary of name to test class.
    """
    config = ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'fixme.cfg'))

    result = {}
    regression_dir = os.path.dirname(__file__)
    for name in os.listdir(regression_dir):
        path = os.path.join(regression_dir, name)
        if os.path.isdir(path):
            result.update(create_classes(name, _find_regression_tests(name, path), config))
    return result

globals().update(_create_test_cases())

