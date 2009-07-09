#   Copyright (C) 2008 Henry Ludemann
#
#   This file is part of the bdec decoder library.
#
#   The bdec decoder library is free software; you can redistribute it
#   and/or modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   The bdec decoder library is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, see
#   <http://www.gnu.org/licenses/>.


"""
Generate test classes for each type of decoder.

See the create_decoder_classes function.
"""

import glob
import itertools
import os
import re
import unittest
import shutil
import subprocess
import stat
import StringIO
import xml.etree.ElementTree

import bdec
import bdec.data as dt
import bdec.output.xmlout as xmlout
import bdec.compiler as comp

def _is_xml_text_equal(a, b):
    a = a.text or ""
    b = b.text or ""
    return a.strip() == b.strip()

def _get_elem_text(a):
    attribs = ' '.join('%s="%s"' % (name, value) for name, value in a.attrib.items())
    text = a.text or ""
    return "<%s %s>%s</%s>" % (a.tag, attribs, text.strip(), a.tag)

def assert_xml_equivalent(expected, actual):
    a = xml.etree.ElementTree.iterparse(StringIO.StringIO(expected), ['start', 'end'])
    b = xml.etree.ElementTree.iterparse(StringIO.StringIO(actual), ['start', 'end'])
    for (a_event, a_elem), (b_event, b_elem) in itertools.izip(a, b):
        if a_event != b_event or a_elem.tag != b_elem.tag or \
                a_elem.attrib != b_elem.attrib or \
                (a_event == 'end' and not _is_xml_text_equal(a_elem, b_elem)):
            raise Exception("expected '%s', got '%s'" % (_get_elem_text(a_elem), _get_elem_text(b_elem)))

def _find_executable(name):
    for path in os.environ['PATH'].split(os.pathsep):
        full_path = os.path.join(path, name)
        try:
            statinfo = os.stat(full_path)
            if stat.S_ISREG(statinfo[stat.ST_MODE]):
                return full_path
        except OSError:
            pass
    return None

def _get_valgrind():
    path =  _find_executable('valgrind')
    if path is None:
        print 'Failed to find valgrind! Code will not be tested with valgrind.'
    return path

def generate(spec, common, details):
    """Create a compiled decoder for a specification in the test directory.

    Doesn't attempt to compile the specification.

    spec -- The specification to compile.
    common -- The common entries from the specification.
    details -- Object containing information on how and where to compile this
        specification. """
    if os.path.exists(details.TEST_DIR):
        shutil.rmtree(details.TEST_DIR)
    os.mkdir(details.TEST_DIR)

    comp.generate_code(spec, details.LANGUAGE, details.TEST_DIR, common)

def compile_and_run(data, details):
    """Compile a previously generated decoder, and use it to decode a data file.

    data -- The data to be decoded.
    details -- Contains information on the generated decoder, and how to
        compile it.
    """
    files = glob.glob(os.path.join(details.TEST_DIR, '*.%s' % details.FILE_TYPE))
    command = [details.COMPILER] + details.COMPILER_FLAGS + [details.EXECUTABLE] + files
    if subprocess.call(command) != 0:
        raise Exception('Failed to compile!')

    if not isinstance(data, str):
        data = data.read()

    filename = os.path.join(details.TEST_DIR, 'data.bin')
    datafile = open(filename, 'wb')
    datafile.write(data)
    datafile.close()

    command = [details.EXECUTABLE, filename]
    if details.VALGRIND is not None:
        command = [details.VALGRIND, '--tool=memcheck', '--leak-check=full'] + command
    decode = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    xml = decode.stdout.read()
    stderr = decode.stderr.read()
    if details.VALGRIND is not None:
        match = re.search('ERROR SUMMARY: (\d+) errors', stderr)
        assert match is not None, stderr
        assert match.group(1) == '0', stderr

    return decode.wait(), xml

class _CompiledDecoder:
    """Base class for testing decoders that are compiled."""
    TEST_DIR = os.path.join(os.path.dirname(__file__), 'temp')
    EXECUTABLE = os.path.join(TEST_DIR, 'decode')
    VALGRIND = _get_valgrind()

    def _decode_file(self, spec, common, data):
        """Return a tuple containing the exit code and the decoded xml."""
        generate(spec, common, self)
        (exitstatus, xml) = compile_and_run(data, self)

        if exitstatus == 0:
            # Validate the output against the python output
            exit_code, expected = _PythonDecoder()._decode_file(spec, common, data)
            if exit_code != 0:
                raise Exception("Python decode failed for when creating expected xml (got %i)", exit_code)
            assert_xml_equivalent(expected, xml)
        return exitstatus, xml


class _CDecoder(_CompiledDecoder):
    # We compile using g++ because it is stricter than gcc
    COMPILER = "g++"
    COMPILER_FLAGS = ["-Wall", "-Werror", '-g', '-o']
    FILE_TYPE = "c"
    LANGUAGE = "c"


class _PythonDecoder:
    """Use the builtin python decoder for the tests."""
    def _decode_file(self, spec, common, sourcefile):
        data = dt.Data(sourcefile)
        xml = StringIO.StringIO()
        try:
            return 0, xmlout.to_string(spec, data)
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
