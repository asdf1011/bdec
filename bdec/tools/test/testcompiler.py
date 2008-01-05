
import glob
import itertools
import operator
import os
import os.path
import shutil
import StringIO
import subprocess
import unittest
import xml.etree.ElementTree

import bdec.choice as chc
import bdec.data as dt
import bdec.field as fld
import bdec.output.xmlout as xmlout
import bdec.sequence as seq
import bdec.sequenceof as sof
import bdec.spec.expression as expr
import bdec.tools.compiler as comp

import sys


class _CompilerTests:
    """
    Set of test cases to test basic compiler functionality.
    """

    TEST_DIR = os.path.join(os.path.dirname(__file__), 'temp')
    EXECUTABLE = os.path.join(TEST_DIR, 'decode')

    def _compile(self, spec, common):
        if os.path.exists(self.TEST_DIR):
            shutil.rmtree(self.TEST_DIR)
        os.mkdir(self.TEST_DIR)

        comp.generate_code(spec, self.TEMPLATE_PATH, self.TEST_DIR, common)

        files = glob.glob(os.path.join(self.TEST_DIR, '*.%s' % self.FILE_TYPE))
        if subprocess.call([self.COMPILER] + self.COMPILER_FLAGS + [self.EXECUTABLE] + files) != 0:
            self.fail('Failed to compile!')

    def _decode_file(self, filename):
        """
        Returns the exit code and the decoded xml.
        """
        raise NotImplementedError()

    def _is_xml_text_equal(self, a, b):
        a = a.text or ""
        b = b.text or ""
        return a.strip() == b.strip()

    def _get_elem_text(self, a):
        attribs = ' '.join('%s=%s' for name, value in a.attrib.itervalues())
        text = a.text or ""
        return "<%s %s>%s ..." % (a.tag, attribs, text.strip())

    def _compare_xml(self, expected, actual):
        a = xml.etree.ElementTree.iterparse(StringIO.StringIO(expected), ['start', 'end'])
        b = xml.etree.ElementTree.iterparse(StringIO.StringIO(actual), ['start', 'end'])
        for (a_event, a_elem), (b_event, b_elem) in itertools.izip(a, b):
            if a_event != b_event or a_elem.tag != b_elem.tag or \
                    a_elem.attrib != b_elem.attrib or \
                    not self._is_xml_text_equal(a_elem, b_elem):
                self.fail("expected '%s', got '%s'" % (self._get_elem_text(a_elem), self._get_elem_text(b_elem)))

    def _decode(self, spec, data, expected_exit_code=0, expected_xml=None, common=[]):
        self._compile(spec, common)

        data_filename = os.path.join(self.TEST_DIR, 'data.bin')
        datafile = open(data_filename, 'wb')
        datafile.write(data)
        datafile.close()
        exit_code, xml = self._decode_file(data_filename)
        self.assertEqual(expected_exit_code, exit_code)

        if exit_code == 0:
            if expected_xml is None:
                # Take the xml output, and ensure the re-encoded data has the same
                # binary value.
                binary = str(reduce(lambda a,b:a+b, xmlout.encode(spec, xml)))
                self.assertEqual(data, binary)
            else:
                self._compare_xml(expected_xml, xml)

    def _decode_failure(self, spec, data, common=[]):
        self._decode(spec, data, 3, common=common)

    def test_basic_decode(self):
        spec = seq.Sequence('blah', [fld.Field('hello', 8, fld.Field.INTEGER)])
        self._decode(spec, 'a')

    def test_sequence_in_sequence(self):
        spec = seq.Sequence('blah', [seq.Sequence('hello', [fld.Field('world', 8, fld.Field.INTEGER)]), fld.Field('bob', 8, fld.Field.INTEGER)])
        self._decode(spec, 'ab')

    def test_common_sequence(self):
        a = seq.Sequence('a', [fld.Field('a1', 8, fld.Field.INTEGER), fld.Field('a2', 8, fld.Field.INTEGER)])
        b = seq.Sequence('b', [a])
        spec = seq.Sequence('blah', [a, b])
        self._decode(spec, 'abcd', common=[a])
        self.assertTrue(os.path.exists(os.path.join(self.TEST_DIR, 'blah.%s' % self.FILE_TYPE)))
        self.assertTrue(os.path.exists(os.path.join(self.TEST_DIR, 'a.%s' % self.FILE_TYPE)))

    def test_decode_string(self):
        spec = seq.Sequence('blah', [fld.Field('bob', 48, fld.Field.TEXT)])
        self._decode(spec, 'rabbit')

    def test_expected_value(self):
        spec = seq.Sequence('blah', [fld.Field('bob', 8, fld.Field.INTEGER, expected=dt.Data('a'))])
        self._decode(spec, 'a')
        self._decode_failure(spec, 'b')

    def test_binary_expected_value(self):
        spec = seq.Sequence('blah', [fld.Field('bob', 8, fld.Field.BINARY, expected=dt.Data('a'))])
        self._decode(spec, 'a')
        self._decode_failure(spec, 'b')

    def test_long_binary_expected_value(self):
        spec = seq.Sequence('blah', [fld.Field('bob', 42, fld.Field.BINARY, expected=dt.Data('abcde\xf0', start=0, end=42)), fld.Field('extra', length=6)])
        self._decode(spec, 'abcde\xf0')
        self._decode_failure(spec, 'abcde\x40')

    def test_expected_text_value(self):
        spec = seq.Sequence('blah', [fld.Field('bob', 40, fld.Field.TEXT, expected=dt.Data('hello'))])
        self._decode(spec, 'hello')
        self._decode_failure(spec, 'hella')
        self._decode_failure(spec, 'hell')

    def test_sequence_decode_failure(self):
        spec = seq.Sequence('blah', [seq.Sequence('dog', [fld.Field('cat', 8, fld.Field.INTEGER, expected=dt.Data('a'))])])
        self._decode(spec, 'a')
        self._decode_failure(spec, 'b')

    def test_not_enough_data(self):
        spec = seq.Sequence('blah', [fld.Field('cat', 8, fld.Field.INTEGER)])
        self._decode_failure(spec, '')
        self._decode(spec, 'a')

    def test_integer_encoding(self):
        spec = seq.Sequence('blah', [fld.Field('cat', 16, fld.Field.INTEGER, encoding=fld.Field.BIG_ENDIAN)])
        self._decode(spec, 'ab')

        spec = seq.Sequence('blah', [fld.Field('cat', 16, fld.Field.INTEGER, encoding=fld.Field.LITTLE_ENDIAN)])
        self._decode(spec, 'ab')

    def test_choice(self):
        a = seq.Sequence('sue', [fld.Field('a', 8, fld.Field.INTEGER, expected=dt.Data('a'))])
        b = seq.Sequence('bob', [fld.Field('b', 8, fld.Field.INTEGER, expected=dt.Data('b'))])
        spec = chc.Choice('blah', [a, b])
        self._decode(spec, 'a')
        self._decode(spec, 'b')
        self._decode_failure(spec, 'c')

    def test_sequenceof(self):
        a = fld.Field('a', 8, fld.Field.INTEGER, expected=dt.Data('a'))
        b = fld.Field('x', 8, fld.Field.INTEGER)
        spec = sof.SequenceOf('blah', seq.Sequence('dog', [a, b]), 4)
        self._decode(spec, 'a1a2a3a4')
        self._decode(spec, 'axa8aaac')
        self._decode_failure(spec, 'a1a3a3b4')

    def test_unaligned_bits(self):
        a = fld.Field('a', 1, fld.Field.INTEGER)
        b = fld.Field('b', 3, fld.Field.INTEGER)
        c = fld.Field('c', 8, fld.Field.INTEGER)
        d = fld.Field('d', 4, fld.Field.INTEGER)
        spec = seq.Sequence('blah', [a,b,c,d])
        self._decode(spec, 'ab')

    def test_variable_length_integer(self):
        a = fld.Field('a', 8, fld.Field.INTEGER)
        value = expr.ValueResult('a')
        b = fld.Field('b', expr.Delayed(operator.__mul__, value, 8), fld.Field.INTEGER)
        spec = seq.Sequence('blah', [a,b])
        expected_xml = """
           <blah>
              <a>3</a>
              <b>83</b>
           </blah> """
        self._decode(spec, '\x03\x00\x00\x53', expected_xml=expected_xml)

    def test_hex_decode(self):
        a = fld.Field('a', 32, fld.Field.HEX)
        spec = seq.Sequence('blah', [a])
        self._decode(spec, 'abcd')

    def test_bits_decode(self):
        a = fld.Field('a', 6, fld.Field.INTEGER)
        b = fld.Field('b', 6, fld.Field.BINARY)
        c = fld.Field('c', 4, fld.Field.INTEGER)
        spec = seq.Sequence('blah', [a, b, c])
        self._decode(spec, 'ab')

    def test_end_sequenceof(self):
        # Note that we are wrapping the bugs in sequences because we cannot
        # store fields directly under a choice (see issue 20).
        null = seq.Sequence('fixa', [fld.Field('null', 8, fld.Field.INTEGER, expected=dt.Data('\x00'))])
        char = seq.Sequence('fixb', [fld.Field('character', 8, fld.Field.TEXT)])
        spec = sof.SequenceOf('blah', chc.Choice('byte', [null, char]), None, end_entries=[(null, 0)])
        self._decode(spec, 'rabbit\0')

    def test_variable_sequenceof(self):
        a1 = fld.Field('a1', 8, fld.Field.INTEGER)
        a = seq.Sequence('a', [a1])
        value = expr.ValueResult('a.a1')

        b1 = fld.Field('b2', 8, fld.Field.INTEGER)
        ba = seq.Sequence('b1', [b1])
        b = sof.SequenceOf('b', ba, value)
        spec = seq.Sequence('blah', [a,b])
        # We don't attempt to re-encode the data, because the python encoder
        # cannot do it.
        expected_xml = """
           <blah>
              <a>
                 <a1>3</a1>
              </a>
              <b>
                 <b1><b2>0</b2></b1>
                 <b1><b2>0</b2></b1>
                 <b1><b2>83</b2></b1>
              </b>
           </blah> """
        self._decode(spec, '\x03\x00\x00\x53', expected_xml=expected_xml)

    def test_length_reference(self):
        length_total = fld.Field('length total', 8, fld.Field.INTEGER)
        total_length_expr = expr.ValueResult('length total')
        header_length = fld.Field('length header', 8, fld.Field.INTEGER)
        header_length_expr = expr.ValueResult('length header')
        header = fld.Field('header', expr.Delayed(operator.__mul__, header_length_expr, 8), fld.Field.TEXT)
        header_data_length = expr.LengthResult('header')
        data_length = expr.Delayed(operator.__sub__, expr.Delayed(operator.__mul__, total_length_expr, 8), header_data_length)
        data = fld.Field('data', data_length, fld.Field.TEXT)
        spec = seq.Sequence('blah', [length_total, header_length, header, data])
        expected_xml = """
           <blah>
              <length-total>10</length-total>
              <length-header>6</length-header>
              <header>header</header>
              <data>data</data>
           </blah> """
        self._decode(spec, '\x0a\x06headerdata', expected_xml=expected_xml)

    def test_fields_under_choice(self):
        a = fld.Field('a', 8, fld.Field.INTEGER, expected=dt.Data('a'))
        b = fld.Field('b', 8, fld.Field.INTEGER, expected=dt.Data('b'))
        spec = chc.Choice('blah', [a, b])
        self._decode(spec, 'a')
        self._decode(spec, 'b')
        self._decode_failure(spec, 'c')

    def test_name_escaping(self):
        a = fld.Field('a with spaces', 8, fld.Field.INTEGER)
        b = seq.Sequence('b with a :', [a])
        c = fld.Field('c', 8, fld.Field.INTEGER)
        d = seq.Sequence('d', [c])
        blah = seq.Sequence('blah', [b, d])
        self._decode(blah, 'xy', common=[blah, d])

    def test_duplicate_names_at_different_level(self):
        a = seq.Sequence('a', [fld.Field('c', 8, fld.Field.INTEGER)])
        b = seq.Sequence('b', [seq.Sequence('a', [fld.Field('d', 8, fld.Field.INTEGER)])])
        blah = seq.Sequence('blah', [a, b])
        self._decode(blah, '\x09\x06', common=[blah, a,b])

    def test_duplicate_names_in_sequence(self):
        b = seq.Sequence('a', [fld.Field('b', 8, fld.Field.INTEGER), fld.Field('b', 8, fld.Field.INTEGER)])
        blah = seq.Sequence('blah', [b])

        # We don't attempt to re-encode the data, because the python encoder
        # cannot do it (see issue41).
        expected_xml = """
           <blah>
              <a>
                 <b>9</b>
                 <b>6</b>
              </a>
           </blah> """
        self._decode(blah, '\x09\x06', expected_xml=expected_xml)

    def test_duplicate_names_in_choice(self):
        b = chc.Choice('a', [fld.Field('a', 8, fld.Field.INTEGER, expected=dt.Data('a')), fld.Field('a', 8, fld.Field.INTEGER)])
        blah = seq.Sequence('blah', [b])
        self._decode(blah, 'a')
        self._decode(blah, 'b')

    def test_duplicate_complex_embedded_entries(self):
        a = seq.Sequence('a', [seq.Sequence('a', [fld.Field('a', 8, fld.Field.INTEGER)])])
        blah = seq.Sequence('blah', [a])
        self._decode(blah, 'x')

    def test_reserved_word(self):
        a = fld.Field('int', 8, fld.Field.INTEGER)
        blah = seq.Sequence('blah', [a])
        self._decode(blah, '\x45')

    def test_duplicate_name_to_same_instance(self):
        a = fld.Field('a', 8, fld.Field.INTEGER)
        blah = seq.Sequence('blah', [a, a])

        # We don't attempt to re-encode the data, because the python encoder
        # cannot do it (see issue41).
        expected_xml = """
           <blah>
              <a>1</a>
              <a>2</a>
           </blah> """
        self._decode(blah, '\x01\x02', common=[blah, a], expected_xml=expected_xml)

    def test_min(self):
        a = fld.Field('a', 8, fld.Field.INTEGER, min=8)
        b = fld.Field('b', 8, fld.Field.INTEGER)
        blah = chc.Choice('blah', [a,b])
        self._decode(blah, '\x08')
        self._decode(blah, '\x07')

    def test_max(self):
        a = fld.Field('a', 8, fld.Field.INTEGER, max=8)
        b = fld.Field('b', 8, fld.Field.INTEGER)
        blah = chc.Choice('blah', [a,b])
        self._decode(blah, '\x08')
        self._decode(blah, '\x09')

    def test_recursive_entries(self):
        # There was a problem with creating include files for items that cross
        # reference each other. Test that we can create a decoder for a
        # recursive specification.
        embed_b = chc.Choice('embed b', [fld.Field('null', 8, expected=dt.Data('\x00'))])
        a = seq.Sequence('a', [fld.Field('id', 8, fld.Field.TEXT, expected=dt.Data('a')), embed_b])

        embed_a = chc.Choice('embed a', [fld.Field('null', 8, expected=dt.Data('\x00')), a])
        b = seq.Sequence('b', [fld.Field('id', 8, fld.Field.TEXT, expected=dt.Data('b')), embed_a])
        embed_b.children.append(b)

        self._decode(b, 'bababa\00', common=[a,b])
        self._decode(b, 'b\00', common=[a,b])
        self._decode_failure(b, 'bac', common=[a,b])

class TestC(_CompilerTests, unittest.TestCase):
    COMPILER = "gcc"
    COMPILER_FLAGS = ["-Wall", '-g', '-o']
    FILE_TYPE = "c"
    TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'templates', 'c')


    def _decode_file(self, filename):
        decode = subprocess.Popen([self.EXECUTABLE, filename], stdout=subprocess.PIPE)
        xml = decode.stdout.read()
        return decode.wait(), xml

