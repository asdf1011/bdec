
"""
Generate test classes for each type of decoder.

See the create_decoder_classes function.
"""

import glob
import os
import unittest
import shutil
import subprocess
import StringIO

import bdec
import bdec.data as dt
import bdec.output.xmlout as xmlout
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

    def _decode_file(self, spec, common, data):
        """Return a tuple containing the exit code and the decoded xml."""
        self._compile(spec, common)

        filename = os.path.join(self.TEST_DIR, 'data.bin')
        datafile = open(filename, 'wb')
        if isinstance(data, str):
            datafile.write(data)
        else:
            datafile.write(data.read())
        datafile.close()

        decode = subprocess.Popen([self.EXECUTABLE, filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        xml = decode.stdout.read()
        return decode.wait(), xml


class _CDecoder(_CompiledDecoder):
    COMPILER = "gcc"
    COMPILER_FLAGS = ["-Wall", '-g', '-o']
    FILE_TYPE = "c"
    TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'c')


class _PythonDecoder:
    """Use the builtin python decoder for the tests."""
    def _decode_file(self, spec, common, sourcefile):
        data = dt.Data(sourcefile)
        xml = StringIO.StringIO()
        try:
            return 0, xmlout.to_string(spec, data, verbose=True)
        except bdec.DecodeError:
            return 3, ""

def create_decoder_classes(base_classes, module):
    """
    Return a dictionary of classes derived from unittest.TestCase.

    There will be a derived base class for each type of decoder (eg: python, 
    C, ...). The key of the dictionary is the name of the class, the value
    the class itself.
    
    Each class will have a _decode_file method which can be used to perform
    the decode.

    Can be used by globals().update(create_decoder_classes(...))

    Arguments:
    base_classes -- a tuple containing (base class, name)
    module -- the module name the generated classes will part of
    """
    decoders = [(_CDecoder, 'C'), (_PythonDecoder, 'Python')]
    result = {}
    for base, prefix in base_classes:
        for decoder, name in decoders:
            test_name = "Test%s%s" % (prefix, name)
            result[test_name] = type(test_name, (unittest.TestCase, decoder, base), {})
            result[test_name].__module__ = module
    return result
