
import glob
import os
import os.path
import shutil
import subprocess
import unittest

import bdec.field as fld
import bdec.output.xmlout as xmlout
import bdec.sequence as seq
import bdec.tools.compiler as comp


class _CompilerTests:
    """
    Set of test cases to test basic compiler functionality.
    """

    TEST_DIR = os.path.join(os.path.dirname(__file__), 'temp')
    EXECUTABLE = os.path.join(TEST_DIR, 'decode')

    def _compile(self, spec):
        if os.path.exists(self.TEST_DIR):
            shutil.rmtree(self.TEST_DIR)
        os.mkdir(self.TEST_DIR)
        main = file(os.path.join(self.TEST_DIR, "main.%s" % self.FILE_TYPE), 'w')
        main.write(self.ENTRYPOINT)
        main.close()

        comp.generate_code(spec, self.TEMPLATE_PATH, self.TEST_DIR)

        files = glob.glob(os.path.join(self.TEST_DIR, '*.%s' % self.FILE_TYPE))
        if subprocess.call([self.COMPILER] + self.COMPILER_FLAGS + [self.EXECUTABLE] + files) != 0:
            self.fail('Failed to compile!')

    def _decode_file(self, filename):
        """
        Returns the exit code and the decoded xml.
        """
        raise NotImplementedError()

    def _decode(self, spec, data):
        self._compile(spec)

        data_filename = os.path.join(self.TEST_DIR, 'data.bin')
        datafile = open(data_filename, 'wb')
        datafile.write(data)
        datafile.close()
        exit_code, xml = self._decode_file(data_filename)
        if exit_code != 0:
            self.fail('Failed to decode data (exit code=%i)!' % exit_code)

        # Take the xml output, and ensure the re-encoded data has the same
        # binary value.
        binary = str(reduce(lambda a,b:a+b, xmlout.encode(spec, xml)))
        self.assertEqual(data, binary)

    def test_basic_decode(self):
        spec = seq.Sequence('blah', [fld.Field('hello', 8, fld.Field.INTEGER)])
        self._decode(spec, 'a')

    def test_sequence_in_sequence(self):
        spec = seq.Sequence('blah', [seq.Sequence('hello', [fld.Field('world', 8, fld.Field.INTEGER)])])
        self._decode(spec, 'a')


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
            char* data = malloc(length);
            fread(data, length, length, datafile);
            fclose(datafile);

            /* Attempt to decode the file */
            Buffer buffer = {data};
            blah* result = decode_blah(&buffer);
            if (result == 0)
            {
                /* Decode failed! */
                return 3;
            }

            /* Print the decoded data */
            print_xml_blah(result);

            return 0;
        }\n"""

    def _decode_file(self, filename):
        decode = subprocess.Popen([self.EXECUTABLE, filename], stdout=subprocess.PIPE)
        xml = decode.stdout.read()
        return decode.wait(), xml

