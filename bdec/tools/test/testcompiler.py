
import glob
import operator
import os
import os.path
import shutil
import subprocess
import unittest

import bdec.choice as chc
import bdec.data as dt
import bdec.field as fld
import bdec.output.xmlout as xmlout
import bdec.sequence as seq
import bdec.sequenceof as sof
import bdec.spec.expression as expr
import bdec.tools.compiler as comp

import sys

file('hmm', 'w').write("\n".join(sys.modules))

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
        main = file(os.path.join(self.TEST_DIR, "main.%s" % self.FILE_TYPE), 'w')
        main.write(self.ENTRYPOINT)
        main.close()

        comp.generate_code(spec, self.TEMPLATE_PATH, self.TEST_DIR, common)

        files = glob.glob(os.path.join(self.TEST_DIR, '*.%s' % self.FILE_TYPE))
        if subprocess.call([self.COMPILER] + self.COMPILER_FLAGS + [self.EXECUTABLE] + files) != 0:
            self.fail('Failed to compile!')

    def _decode_file(self, filename):
        """
        Returns the exit code and the decoded xml.
        """
        raise NotImplementedError()

    def _decode(self, spec, data, expected_exit_code=0, do_encode=True, common=[]):
        self._compile(spec, common)

        data_filename = os.path.join(self.TEST_DIR, 'data.bin')
        datafile = open(data_filename, 'wb')
        datafile.write(data)
        datafile.close()
        exit_code, xml = self._decode_file(data_filename)
        self.assertEqual(expected_exit_code, exit_code)

        if exit_code == 0 and do_encode:
            # Take the xml output, and ensure the re-encoded data has the same
            # binary value.
            binary = str(reduce(lambda a,b:a+b, xmlout.encode(spec, xml)))
            self.assertEqual(data, binary)

    def _decode_failure(self, spec, data):
        self._decode(spec, data, 3)

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
        value = expr.ValueResult()
        value.add_entry(a)
        b = fld.Field('b', expr.Delayed(operator.__mul__, value, 8), fld.Field.INTEGER)
        spec = seq.Sequence('blah', [a,b])
        # We don't attempt to re-encode the data, because the python encoder
        # cannot do it.
        self._decode(spec, '\x03\x00\x00\x53', do_encode=False)

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
        value = expr.ValueResult()
        value.add_entry(a1)
        a = seq.Sequence('a', [a1])

        b1 = fld.Field('b2', 8, fld.Field.INTEGER)
        ba = seq.Sequence('b1', [b1])
        b = sof.SequenceOf('b', ba, value)
        spec = seq.Sequence('blah', [a,b])
        # We don't attempt to re-encode the data, because the python encoder
        # cannot do it.
        self._decode(spec, '\x03\x00\x00\x53', do_encode=False)

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

class TestVariableReference(unittest.TestCase):
    def test_direct_children(self):
        a = fld.Field('a', 8)
        value = expr.ValueResult()
        value.add_entry(a)
        b = fld.Field('b', value)
        spec = seq.Sequence('blah', [a,b])

        vars = comp._VariableReference(spec)
        self.assertEqual(['a'], vars.get_locals(spec))
        self.assertTrue(vars.is_referenced(a))
        self.assertFalse(vars.is_referenced(b))
        self.assertEqual([], vars.get_locals(a))

    def test_sub_children(self):
        a1 = fld.Field('a1', 8)
        a = seq.Sequence('a', [a1])
        value = expr.ValueResult()
        value.add_entry(a1)
        b1 = fld.Field('b1', value)
        b = seq.Sequence('b', [b1])
        spec = seq.Sequence('blah', [a,b])

        vars = comp._VariableReference(spec)
        self.assertEqual(['a1'], vars.get_locals(spec))
        # Note that despite containing a referenced entry, it isn't a local (as
        # it is passed up to the parent entry).
        self.assertEqual([], vars.get_locals(a))

        # Now check what parameters are passed in and out
        self.assertEqual(set(), vars.get_params(spec))
        self.assertEqual(set([comp.Param('a1', comp.Param.OUT)]), vars.get_params(a))
        self.assertEqual(set([comp.Param('a1', comp.Param.IN)]), vars.get_params(b))


class TestC(_CompilerTests, unittest.TestCase):
    COMPILER = "gcc"
    COMPILER_FLAGS = ["-Wall", '-g', '-o']
    FILE_TYPE = "c"
    TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'templates', 'c')

    ENTRYPOINT = """
        #include <stdio.h>
        #include <stdlib.h>

        #include "blah.h"
        #include "buffer.h"

        int main(int argc, char* argv[])
        {
            if (argc != 2)
            {
                /* Bad number of arguments */
                return 1;
            }
            char* filename = argv[1];
            FILE* datafile = fopen(filename, "rb");
            if (datafile == 0)
            {
                /* Failed to open file */
                return 2;
            }
            fseek(datafile, 0, SEEK_END);
            long int length = ftell(datafile);
            fseek(datafile, 0, SEEK_SET);

            /* Load the data file into memory */
            unsigned char* data = malloc(length);
            fread(data, length, length, datafile);
            fclose(datafile);

            /* Attempt to decode the file */
            BitBuffer buffer = {data, 0, length * 8};
            Blah result;
            if (!decodeBlah(&buffer, &result))
            {
                /* Decode failed! */
                return 3;
            }

            /* Print the decoded data */
            printXmlBlah(&result);

            return 0;
        }\n"""

    def _decode_file(self, filename):
        decode = subprocess.Popen([self.EXECUTABLE, filename], stdout=subprocess.PIPE)
        xml = decode.stdout.read()
        return decode.wait(), xml

