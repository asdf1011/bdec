
import itertools
import operator
import os
import os.path
import StringIO
import unittest
import xml.etree.ElementTree

import bdec.choice as chc
import bdec.data as dt
import bdec.field as fld
import bdec.output.xmlout as xmlout
import bdec.sequence as seq
import bdec.sequenceof as sof
import bdec.spec.expression as expr
from bdec.test.decoders import create_decoder_classes

import sys


class _CompilerTests:
    """
    Set of test cases to test basic compiler functionality.
    """

    def _decode_file(self, spec, common, data):
        """Return a tuple containing the exit code and the decoded xml."""
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
        exit_code, xml = self._decode_file(spec, common, StringIO.StringIO(data))
        self.assertEqual(expected_exit_code, exit_code)

        if exit_code == 0:
            if expected_xml is None:
                # Take the xml output, and ensure the re-encoded data has the same
                # binary value.
                binary = reduce(lambda a,b:a+b, xmlout.encode(spec, xml)).bytes()
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
        b = fld.Field('b', expr.Delayed(operator.__mul__, value, expr.Constant(8)), fld.Field.INTEGER)
        spec = seq.Sequence('blah', [a,b])
        expected_xml = """
           <blah>
              <a>3</a>
              <b>83</b>
           </blah> """
        self._decode(spec, '\x03\x00\x00\x53', expected_xml=expected_xml)

    def test_entry_with_multiple_outputs(self):
        # There was a problem with an entry that had multiple outputs from a
        # single child (in this test, 'c' has outputs for 'a' and 'b', both of
        # which are passed through 'problem').
        a = fld.Field('a', 8, fld.Field.INTEGER)
        b = fld.Field('b', 8, fld.Field.INTEGER)
        c = seq.Sequence('c', [a, b])
        problem = seq.Sequence('problem', [c])

        value_a = expr.ValueResult('problem.c.a')
        value_b = expr.ValueResult('problem.c.b')
        d = fld.Field('d', value_a)
        e = fld.Field('e', value_b)
        spec = seq.Sequence('spec', [problem, d, e])
        expected_xml = "<spec><problem><c><a>6</a><b>2</b></c></problem><d>111100</d><e>01</e></spec>"
        self._decode(spec, '\x06\x02\xf1', expected_xml=expected_xml)

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
        spec = sof.SequenceOf('blah', chc.Choice('byte', [null, char]), None, end_entries=[null])
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
        header = fld.Field('header', expr.Delayed(operator.__mul__, header_length_expr, expr.Constant(8)), fld.Field.TEXT)
        header_data_length = expr.LengthResult('header')
        data_length = expr.Delayed(operator.__sub__, expr.Delayed(operator.__mul__, total_length_expr, expr.Constant(8)), header_data_length)
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
        self._decode(a, '\x08')
        self._decode_failure(a, '\x07')

    def test_max(self):
        a = fld.Field('a', 8, fld.Field.INTEGER, max=8)
        self._decode(a, '\x08')
        self._decode_failure(a, '\x09')

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

    def test_sequenceof_with_length(self):
        buffer = sof.SequenceOf('databuffer', fld.Field('data', 8), None, length=32)
        self._decode(buffer, 'baba')

    def test_sequenceof_failure(self):
        text = sof.SequenceOf('a', fld.Field('data', 8, expected=dt.Data('a')), count=2)
        buffer = sof.SequenceOf('databuffer', text, count=3)
        other = fld.Field('fallback', length=48)
        self._decode(chc.Choice('blah', [buffer, other]), 'aaabaa')

    def test_sequence_value(self):
        digit = seq.Sequence('digit', [fld.Field('text digit', 8, fld.Field.INTEGER, min=48, max=57)], value=expr.compile("${text digit} - 48"))
        two_digits = seq.Sequence('two digits',
                [seq.Sequence('digit 1', [digit]), seq.Sequence('digit 2', [digit])],
                value=expr.compile("${digit 1.digit} * 10 + ${digit 2.digit}"))
        buffer = fld.Field('buffer', expr.compile("${two digits} * 8"), fld.Field.TEXT)
        a = seq.Sequence('a', [two_digits, buffer])
        expected = """<a>
            <two-digits>
              <digit-1><digit><text-digit>50</text-digit></digit></digit-1>
              <digit-2><digit><text-digit>49</text-digit></digit></digit-2>
            </two-digits>
            <buffer>xxxxxxxxxxxxxxxxxxxxx</buffer>
          </a>"""
        self._decode(a, '21' + 'x' * 21, expected_xml=expected, common=[digit, two_digits, a])

globals().update(create_decoder_classes([(_CompilerTests, 'SimpleDecode')], __name__))
