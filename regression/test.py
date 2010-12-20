
from ConfigParser import ConfigParser
import glob
import os.path

from bdec.test.decoders import create_classes

def _find_regression_tests(spec_format, regression_dir):
    specs = glob.glob('%s/*.%s' % (regression_dir, spec_format))
    for path in specs:
        if not path.endswith('.expected.xml'):
            glob_name = os.path.splitext(path)[0]
            name = os.path.split(glob_name)[1]

            failures = []
            successes = []
            binary_files = glob.glob('%s.*.bin' % glob_name)
            binary_files += glob.glob('%s.*.ber' % glob_name)
            binary_files += glob.glob('%s.*.der' % glob_name)
            for data_filename in binary_files:
                if '.failure.' in data_filename:
                    failures.append(data_filename)
                else:
                    successes.append(data_filename)
            yield name, path, successes, failures

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

