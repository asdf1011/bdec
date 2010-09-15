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
from bdec.constraints import Equals
from bdec.choice import Choice
import bdec.data as dt
from bdec.entry import is_hidden
import bdec.field as fld
import bdec.output.xmlout as xmlout
import bdec.compiler as comp

class ExecuteError(Exception):
    def __init__(self, exit_code, stderr):
        self.exit_code = exit_code
        self.stderr = stderr

    def __str__(self):
        return 'Execute failed with exit code %i; %s' % (self.exit_code, self.stderr)

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

_template_cache = {}
def _load_templates_from_cache(language):
    # We cache the results, as it sped up the tests by about 3x.
    try:
        return _template_cache[language]
    except KeyError:
        template_dir = comp.BuiltinTemplate(language)
        _template_cache[language] = comp.load_templates(template_dir)
        return _template_cache[language]

def generate(spec, common, details, should_check_encoding):
    """Create a compiled decoder for a specification in the test directory.

    Doesn't attempt to compile the specification.

    spec -- The specification to compile.
    common -- The common entries from the specification.
    details -- Object containing information on how and where to compile this
        specification. """
    if os.path.exists(details.TEST_DIR):
        shutil.rmtree(details.TEST_DIR)
    os.mkdir(details.TEST_DIR)

    options = {
            'generate_encoder':should_check_encoding,
            }
    comp.generate_code(spec, _load_templates_from_cache(details.LANGUAGE),
            details.TEST_DIR, common, options)

def compile_and_run(data, details, encode_filename=None):
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

    command = [details.EXECUTABLE, '-e', encode_filename, filename]
    if not encode_filename:
        # We don't want to encode; strip out those parameters.
        command = command[0:1] + command[3:4]
    if details.VALGRIND is not None:
        command = [details.VALGRIND, '--tool=memcheck', '--leak-check=full'] + command
    decode = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    xml = decode.stdout.read()
    stderr = decode.stderr.read()
    if details.VALGRIND is not None:
        match = re.search('ERROR SUMMARY: (\d+) errors', stderr)
        assert match is not None, stderr
        assert match.group(1) == '0', stderr

    exit_status = decode.wait()
    if exit_status != 0:
        raise ExecuteError(exit_status, stderr)
    return xml

class _NoExpectedError(Exception):
    pass

def _get_expected(entry):
    for constraint in entry.constraints:
        if isinstance(constraint, Equals):
            return constraint.limit.evaluate({})
    raise _NoExpectedError()

def _decode_visible(spec, data):
    """ Use the spec to decode the given data, returning all visible entries. """
    hidden_count = 0
    for (is_starting, name, entry, data, value) in spec.decode(data):

        is_visible = True
        if isinstance(entry, Choice):
            # Choice entries aren't printed...
            is_visible = False

        if is_starting:
            if hidden_count or is_hidden(name):
                # This entry is hidden; all child entries should also be
                # hidden, even if their names are visible.
                hidden_count += 1
                is_visible = False
        else:
            if hidden_count:
                # We are finishing a hidden entry...
                hidden_count -= 1
                is_visible = False

        if is_visible:
            yield is_starting, name, entry, data, value

def _validate_xml(spec, data, xmltext):
    """Validate the decoded xml.

    We don't just use the internal xml and compare it against the external xm;
    there may be differences in whitespace, and some fields can be represented
    in multiple ways (eg: 5.0 vs 5.00000 vs 5).
    """
    xml_entries = xml.etree.ElementTree.iterparse(StringIO.StringIO(xmltext), ['start', 'end'])
    child_tail=None
    for (is_starting, name, entry, data, expected), (a_event, a_elem) in itertools.izip(_decode_visible(spec, data), xml_entries):
        if is_starting and a_event != 'start':
            raise Exception ("Expected '%s' to be starting, but got '%s' ending" %
                    (name, a_elem.tag))
        if not is_starting and a_event != 'end':
            raise Exception ("Expected '%s' to be ending, but got '%s' starting" %
                    (name, a_elem.tag))
        if xmlout.escape_name(name) != a_elem.tag:
            raise Exception("expected '%s', got '%s'" %
                    (xmlout.escape_name(name), a_elem.tag))
        if not is_starting:
            text = a_elem.text
            if not text or not  text.strip() and child_tail is not None:
                # We don't have a text node for this child; try using its
                # child's trailing text.
                text = child_tail
            if not text or not text.strip():
                # This node doesn't have data; it's possible that it has an
                # expected value, so wasn't printed. Get the expected value
                # from the constraint.
                try:
                    text = _get_expected(entry)
                except _NoExpectedError:
                    # We don't have an expected value; stick with the existing text.
                    pass
            if text is None:
                text = ''

            if expected is not None:
                if isinstance(entry, fld.Field):
                    actual_data = entry.encode_value(text, len(data))
                    actual = entry.decode_value(actual_data)
                else:
                    actual = int(text)
                if expected != actual:
                    # If the value is different, it may be that the data cannot
                    # be represented in xml (eg: a string with a binary
                    # character). Encode and decode the expected value to see if
                    # matches now (being escaped itself...)
                    expected_text = xmlout.xml_strip(unicode(expected))
                    expected_data = entry.encode_value(expected_text, len(data))
                    escaped_expected = entry.decode_value(expected_data)
                    constraint = Equals(escaped_expected)
                    constraint.check(entry, actual, {})
            elif a_elem.text is not None and a_elem.text.strip():
                raise Exception("Expected empty text in entry '%s', got '%s'!" %
                        (a_elem.tag, a_elem.text))
            child_tail=a_elem.tail
        else:
            child_tail=None

def _check_encoded_data(spec, sourcefile, actual, actual_xml, require_exact_encoding):
    sourcefile.seek(0)
    expected = sourcefile.read()
    if actual != expected:
        # The data is different, but it is possibly due to the data being able
        # to be encoded in multiple ways. Try re-decoding the data to compare
        # against the original xml.
        try:
            regenerated_xml = xmlout.to_string(spec, dt.Data(actual))
            assert_xml_equivalent(actual_xml, regenerated_xml)
        except Exception, ex:
            raise Exception('Re-decoding of encoded data failed: %s' % str(ex))

        if require_exact_encoding:
            raise Exception("Encoded data doesn't match, but we require exact encoding!")


class _CompiledDecoder:
    """Base class for testing decoders that are compiled."""
    TEST_DIR = os.path.join(os.path.dirname(__file__), 'temp')
    EXECUTABLE = os.path.join(TEST_DIR, 'decode')
    VALGRIND = _get_valgrind()

    def _decode_file(self, spec, common, data, should_check_encoding=True, require_exact_encoding=False):
        """Return a tuple containing the exit code and the decoded xml."""
        generate(spec, common, self, should_check_encoding)
        encode_filename = os.path.join(self.TEST_DIR, 'encoded.bin') if should_check_encoding else None
        xml = compile_and_run(data, self, encode_filename)

        try:
            _validate_xml(spec, dt.Data(data), xml)
        except bdec.DecodeError, ex:
            raise Exception("Compiled decoder succeeded, but should have failed with: %s" % str(ex))
	if should_check_encoding:
            _check_encoded_data(spec, data, open(encode_filename, 'rb').read(), xml, require_exact_encoding)
        return xml


class _CDecoder(_CompiledDecoder):
    # We compile using g++ because it is stricter than gcc
    COMPILER = "gcc"
    COMPILER_FLAGS = ["-Wall", "-Werror", '-g', '-o']
    FILE_TYPE = "c"
    LANGUAGE = "c"


class _PythonDecoder:
    """Use the builtin python decoder for the tests."""
    def _decode_file(self, spec, common, sourcefile, should_check_encoding=True, require_exact_encoding=False):
        data = dt.Data(sourcefile)
        try:
	    xml = xmlout.to_string(spec, data)
        except bdec.DecodeError, ex:
            raise ExecuteError(3, ex)

	if should_check_encoding:
	    generated_data = xmlout.encode(spec, xml)
            _check_encoded_data(spec, sourcefile, generated_data.bytes(), xml, require_exact_encoding)
	return xml

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
            result[test_name] = type(test_name, (unittest.TestCase, decoder, base), {'language':name})
            result[test_name].__module__ = module
    return result
