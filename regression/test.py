import glob
import os.path
import unittest

from bdec.spec.xmlspec import load
from bdec.test.decoders import create_decoder_classes, assert_xml_equivalent


class _Xml:
    """A base test case for running regression tests on xml specs."""

    def _test_failure(self, spec, common, spec_filename, data_filename):
        datafile = open(data_filename, 'rb')
        (exit_code, xml) = self._decode_file(spec, common, datafile)
        datafile.close()
        if exit_code == 0:
            raise Exception("'%s' should have failed to decode '%s', but succeeded!" % (spec_filename, data_filename))

    def _test_success(self, spec, common, spec_filename, data_filename, expected_xml):
        datafile = open(data_filename, 'rb')
        (exit_code, xml) = self._decode_file(spec, common, datafile)
        datafile.close()
        if exit_code != 0:
            raise Exception("'%s' failed to decode '%s'!" % (spec_filename, data_filename))
        if expected_xml:
            assert_xml_equivalent(xml, expected_xml)

    def _test_spec(self, spec_filename, successes, failures):
        assert successes or failures

        spec, common, lookup = load(spec_filename)
        common = common.values()
        for data_filename in successes:
            expected_xml = None
            expected_filename = '%s.expected.xml' % os.path.splitext(data_filename)[0]
            if os.path.exists(expected_filename):
                xml_file = file(expected_filename, 'r')
                expected_xml = xml_file.read()
                xml_file.close()
            self._test_success(spec, common, spec_filename, data_filename, expected_xml)

        for data_filename in failures:
            self._test_failure(spec, common, spec_filename, data_filename)

def _create_test_method(name, filename, successes, failures):
    result = lambda self: self._test_spec(filename, successes, failures)
    result.__name__ = name
    return result

def _populate_regression_test_methods(cls):
    """Create a regression test methods for a test class.

    The test class will contain  a 'test_XXX' method for each regression test
    specification.

    cls -- The class to create the test methods in.
    """
    xml_dir = os.path.join(os.path.dirname(__file__), 'xml')
    specs = glob.glob('%s/*.xml' % xml_dir)
    for filename in specs:
        if not filename.endswith('.expected.xml'):
            failures = []
            successes = []
            for data_filename in glob.glob('%s.*.bin' % os.path.splitext(filename)[0]):
                if '.failure.' in data_filename:
                    failures.append(data_filename)
                else:
                    successes.append(data_filename)
            name = 'test_%s' % os.path.splitext(os.path.split(filename)[1])[0]
            method = _create_test_method(name, filename, successes, failures)
            setattr(cls, name, method)

_populate_regression_test_methods(_Xml)
globals().update(create_decoder_classes([(_Xml, 'Xml')], __name__))

