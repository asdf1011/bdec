
from ConfigParser import ConfigParser, NoOptionError, NoSectionError
import glob
import os.path
import unittest

from bdec.spec import load_specs
from bdec.test.decoders import create_decoder_classes, assert_xml_equivalent, ExecuteError


class _Regression:
    """A base test case for running regression tests on specfications."""

    def _test_failure(self, spec, common, spec_filename, data_filename, should_encode):
        datafile = open(data_filename, 'rb')
        try:
            xml = self._decode_file(spec, common, datafile, should_encode)
            raise Exception("'%s' should have failed to decode '%s', but succeeded with output:\n%s" % (spec_filename, data_filename, xml))
        except ExecuteError, ex:
            if ex.exit_code != 3:
                # It should have been a decode error...
                raise
        datafile.close()

    def _test_success(self, spec, common, spec_filename, data_filename, expected_xml, should_encode, require_exact_encoding):
        datafile = open(data_filename, 'rb')
        xml = self._decode_file(spec, common, datafile, should_encode, require_exact_encoding)
        datafile.close()
        if expected_xml:
            assert_xml_equivalent(expected_xml, xml)

    def _test_spec(self, name, spec_filename, successes, failures):
        assert successes or failures

        skip = self.skip_list.get('%s/%s' % (self.spec_format, name), '')
        if skip == 'decode':
            print 'Skipping test.'
            return
        elif skip == 'encode':
            should_encode = False
            require_exact_encoding = True
        elif skip == 'encoding-equivalent':
            should_encode = True
            require_exact_encoding = False
        else:
            assert not skip, "Unknown test fixme status '%s'" % skip
            should_encode = True
            require_exact_encoding = True

        spec, common, lookup = load_specs([(spec_filename, None, None)])
        for data_filename in successes:
            expected_xml = None
            expected_filename = '%s.expected.xml' % os.path.splitext(data_filename)[0]
            if os.path.exists(expected_filename):
                xml_file = file(expected_filename, 'r')
                expected_xml = xml_file.read()
                xml_file.close()
            self._test_success(spec, common, spec_filename, data_filename,
                    expected_xml, should_encode, require_exact_encoding)

        for data_filename in failures:
            self._test_failure(spec, common, spec_filename, data_filename, should_encode)

def _create_test_method(name, test_name, filename, successes, failures):
    result = lambda self: self._test_spec(name, filename, successes, failures)
    result.__name__ = test_name
    return result

def _populate_regression_test_methods(cls, regression_dir, extension):
    """Create a regression test methods for a test class.

    The test class will contain  a 'test_XXX' method for each regression test
    specification.

    cls -- The class to create the test methods in.
    regression_dir -- The directory to look for specifications.
    extension -- The extension for this type of specification.
    return -- A list of names of the tests that were added.
    """
    specs = glob.glob('%s/*.%s' % (regression_dir, extension))
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
            test_name = 'test_%s' % name
            method = _create_test_method(name, test_name, path, successes,
                    failures)
            setattr(cls, test_name, method)

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
            clsname = name[0].upper() + name[1:]
            cls = type(clsname, (object, _Regression,), {'spec_format':name})
            _populate_regression_test_methods(cls, path, name)
            result.update(create_decoder_classes([(cls, clsname)], __name__))
    default = dict(config.items('default'))
    for name, cls in result.items():
        cls.skip_list = default.copy()
        cls.skip_list.update(config.items(cls.language))
    return result
globals().update(_create_test_cases())

