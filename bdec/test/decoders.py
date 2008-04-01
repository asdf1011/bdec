
"""
Generate test classes for each type of decoder.

See the create_decoder_classes function.
"""

import glob
import os
import unittest
import shutil
import subprocess

import bdec.tools.compiler as comp

class _CompiledDecoder:
    """Base class for testing decoders that are compiled."""
    TEST_DIR = os.path.join(os.path.dirname(__file__), 'temp')
    EXECUTABLE = os.path.join(TEST_DIR, 'decode')

    def _compile(self, spec, common):
        """Create a compiled decoder."""
        if os.path.exists(self.TEST_DIR):
            shutil.rmtree(self.TEST_DIR)
        os.mkdir(self.TEST_DIR)

        comp.generate_code(spec, self.TEMPLATE_PATH, self.TEST_DIR, common)

        files = glob.glob(os.path.join(self.TEST_DIR, '*.%s' % self.FILE_TYPE))
        if subprocess.call([self.COMPILER] + self.COMPILER_FLAGS + [self.EXECUTABLE] + files) != 0:
            self.fail('Failed to compile!')

    def _decode_file(self, spec, common, sourcefile):
        """Return a tuple containing the exit code and the decoded xml."""
        self._compile(spec, common)

        filename = os.path.join(self.TEST_DIR, 'data.bin')
        datafile = open(filename, 'wb')
        datafile.write(sourcefile.read())
        datafile.close()

        decode = subprocess.Popen([self.EXECUTABLE, filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        xml = decode.stdout.read()
        return decode.wait(), xml


class _CDecoder(_CompiledDecoder):
    COMPILER = "gcc"
    COMPILER_FLAGS = ["-Wall", '-g', '-o']
    FILE_TYPE = "c"
    TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'c')


def create_decoder_classes(base_classes, name_prefix):
    """
    Return a dictionary of classes derived from unittest.TestCase.

    There will be a derived base class for each type of decoder (eg: python, 
    C, ...). The key of the dictionary is the name of the class, the value
    the class itself.
    
    Each class will have a _decode_file method which can be used to perform
    the decode.
    
    Can be used by globals().update(create_decoder_classes(...))
    """
    decoders = [(_CDecoder, 'C')]
    result = {}
    for base in base_classes:
        for decoder, name in decoders:
            test_name = "Test%s%s" % (name_prefix, name)
            result[test_name] = type(test_name, (unittest.TestCase, decoder, base), {})
    return result
