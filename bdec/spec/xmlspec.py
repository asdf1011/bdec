#   Copyright (C) 2008-2009 Henry Ludemann
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

import StringIO
import xml.sax
from xml.sax import saxutils

import bdec.choice as chc
from bdec.constraints import Minimum, Maximum, Equals, NotEquals
import bdec.data as dt
import bdec.entry as ent
import bdec.expression as exp
import bdec.field as fld
import bdec.inspect.param as prm
from bdec.spec import LoadErrorWithLocation
from bdec.spec.references import ReferencedEntry
from bdec.spec.integer import Integers, IntegerError
import bdec.sequence as seq
import bdec.sequenceof as sof

class XmlSpecError(LoadErrorWithLocation):
    pass

class XmlError(XmlSpecError):
    """
    Class for some common xml specification errors.
    """
    def __init__(self, error, filename, locator):
        XmlSpecError.__init__(self, filename, locator)
        self.error = error

    def __str__(self):
        return self._src() + str(self.error)

class EntryHasNoValueError(exp.ExpressionError):
    def __init__(self, entry):
        self.entry = entry

    def __str__(self):
        return "Expressions can only reference entries with a value (%s)" % self.entry

class NonSequenceError(exp.ExpressionError):
    """
    Asked for a child of a non-sequence object.
    """
    def __init__(self, entry):
        self.entry = entry

    def __str__(self):
        return "Expressions can only reference children of sequences (%s)" % self.entry

class OptionMissingNameError(exp.ExpressionError):
    def __init__(self, entry, name, lookup):
        self.entry = entry
        self.name = name
        self.filename, self.line, self.column = lookup[entry]

    def __str__(self):
        return "Choice option missing referenced name '%s'\n\t%s[%i]: %s" % (self.name, self.filename, self.line, self.entry.name)

class XmlExpressionError(XmlSpecError):
    def __init__(self, ex, filename, locator):
        XmlSpecError.__init__(self, filename, locator)
        self.ex = ex

    def __str__(self):
        return self._src() + str(self.ex)


class _Handler(xml.sax.handler.ContentHandler):
    """
    A sax style xml handler for building a decoder from an xml specification
    """
    def __init__(self, filename, references):
        self._filename = filename
        self._stack = []
        self._children = []

        self._handlers = {
            "common" : self._common,
            "choice" : self._choice,
            "end-sequenceof" : self._break,
            "field" : self._field,
            "protocol" : self._protocol,
            "reference" : self._reference,
            "sequence" : self._sequence,
            "sequenceof" : self._sequenceof,
            }
        self.decoder = None

        self.lookup = {}
        self.locator = None
        self._end_sequenceof = False
        self._unresolved_references = []
        self._integers = Integers()
        self._references = references

    def setDocumentLocator(self, locator):
        self.locator = locator

    def _break(self, attrs, children, name, length, breaks):
        if len(attrs) != 0 or len(children) != 0:
            raise self._error("end-sequenceof cannot have attributes or sub-elements")

        assert self._end_sequenceof == False
        self._end_sequenceof = True

    def _error(self, text):
        return XmlError(text, self._filename, self.locator)

    def startElement(self, name, attrs):
        if name not in self._handlers:
            raise self._error("Unrecognised element '%s'!" % name)

        self._stack.append((name, attrs, [], self.locator.getLineNumber(), self.locator.getColumnNumber()))
        self._children.append([])

    def endElement(self, name):
        assert self._stack[-1][0] == name
        (name, attrs, breaks, lineno, colno) = self._stack.pop()

        # We don't pop the children item until after we have called the
        # handler, as it may be used when creating a value reference.
        children = self._children[-1]

        length = None
        if attrs.has_key('length'):
            length = self._parse_expression(attrs['length'])
        entry_name = ""
        if attrs.has_key('name'):
            entry_name = attrs['name']
        entry = self._handlers[name](attrs, children, entry_name, length, breaks)

        # Check for value constraints
        constraints = []
        if attrs.has_key('min'):
            minimum = self._parse_expression(attrs['min'])
            constraints.append(Minimum(minimum))
        if attrs.has_key('max'):
            maximum = self._parse_expression(attrs['max'])
            constraints.append(Maximum(maximum))
        if attrs.has_key('expected'):
            expected = self._parse_expression(attrs['expected'])
            constraints.append(Equals(expected))

        if constraints:
            if isinstance(entry, ReferencedEntry):
                # We found a reference with constraints; create an intermediate
                # sequence that will have the constraints.
                reference = entry
                if not ent.is_hidden(reference.name):
                    reference.name = '%s:' % reference.name
                value = self._parse_expression("${%s}" % reference.name)
                entry = seq.Sequence(entry_name, [reference], value=value)
            entry.constraints += constraints

        self._children.pop()

        if attrs.has_key('if'):
            # This is a 'conditional' entry; only present if the expression in
            # 'if' is true. To decode this, we create a choice with a 'not
            # present' option; this option attempts to decode first, with the
            # condition inverted.
            try:
                not_present = exp.parse_conditional_inverse(attrs['if'])
                not_present.name = 'not present:'
            except exp.ExpressionError, ex:
                raise XmlExpressionError(ex, self._filename, self.locator)
            assert isinstance(not_present, ent.Entry)
            optional = chc.Choice('optional %s' % entry_name, [not_present, entry])
            entry = optional

            self.lookup[not_present] = (self._filename, lineno, colno)
            self.lookup[optional] = (self._filename, lineno, colno)

        if entry is not None:
            if self._end_sequenceof:
                # There is a parent sequence of object that must stop when
                # this entry decodes.
                for name, attrs, breaks, lineno, colnumber in reversed(self._stack):
                    if name == "sequenceof":
                        breaks.append(entry)
                        if isinstance(entry, ReferencedEntry):
                            raise self._error("end-sequenceof cannot be used within a referenced item. Wrap the reference in a sequence (which has the end-sequenceof).")
                        break
                else:
                    raise self._error("end-sequenceof is not surrounded by a sequenceof")
                self._end_sequenceof = False
            self._children[-1].append(entry)

            self.lookup[entry] = (self._filename, lineno, colno)

    def _common(self, attributes, children, name, length, breaks):
        for entry in children:
            self._references.add_common(entry)

    def _protocol(self, attributes, children, name, length, breaks):
        # Add the used integer entries to the specification
        if children:
            self.decoder = children[0]
        else:
            self.decoder = None
        for entry in self._integers.common.values():
            self._references.add_common(entry)

    def _parse_expression(self, text):
        try:
            return exp.compile(text)
        except exp.ExpressionError, ex:
            raise XmlExpressionError(ex, self._filename, self.locator)

    def _reference(self, attributes, children, name, length, breaks):
        type = ""
        try:
            type = attributes["type"]
        except KeyError:
            pass
        if not name and not type:
            raise self._error("Reference entries must non-empty 'name' or 'type' attribute!")
        return self._references.get_common(name, type)

    def _field(self, attributes, children, name, length, breaks):
        format = fld.Field.BINARY
        if length is None:
            raise self._error("Field entries required a 'length' attribute")

        if attributes.has_key('type'):
            lookup = {
                "binary" : fld.Field.BINARY,
                "hex" : fld.Field.HEX,
                "integer" : fld.Field.INTEGER,
                "signed integer" : fld.Field.INTEGER,
                "text" : fld.Field.TEXT,
                "float" : fld.Field.FLOAT,
                }

            format = lookup[attributes['type']]
        encoding = None
        if attributes.has_key('encoding'):
            encoding = attributes['encoding']
            if format is fld.Field.INTEGER:
                _integer_encodings = [fld.Field.LITTLE_ENDIAN, fld.Field.BIG_ENDIAN]
                if encoding not in _integer_encodings:
                    raise self._error("Invalid integer encoding '%s'! Valid values are: %s" % (encoding, ", ".join(_integer_encodings)))

        if format is fld.Field.INTEGER and attributes['type'] == 'signed integer':
            # All signed integers are internally represented as sequences with
            # child big endian numbers. This means the 'core' entries don't
            # have to know about these types.
            try:
                if encoding in [None, fld.Field.BIG_ENDIAN]:
                    integer = self._integers.signed_big_endian(length)
                else:
                    assert encoding == fld.Field.LITTLE_ENDIAN
                    integer = self._integers.signed_litte_endian(length)
            except IntegerError, error:
                raise self._error(str(error))
            return self._references.get_common(name, integer.name)

        # We'll create the field, then use it to create the expected value.
        result = fld.Field(name, length, format, encoding)
        if attributes.has_key('value'):
            # Get the correct object type by encoding, then decoding, the text
            # value.
            expected_text = attributes['value']
            if expected_text.upper()[:2] == "0X":
                # The expected value is in hex, so convert it to a data object.
                try:
                    expected_length = result.length.evaluate({})
                except exp.UndecodedReferenceError:
                    # We don't know the length of the object; assume it'll be
                    # the length of the hex.
                    expected_length = 8 * (len(expected_text) - 2)
                data = dt.Data('\x00' * (expected_length / 8 + 8))
                data += dt.Data.from_hex(expected_text[2:])
                unused = data.pop(len(data) - expected_length)
                if len(unused) and int(unused) != 0:
                    raise self._error('Field is %i bits long, but expected data is longer (%i bits)!' % (expected_length, len(unused) + len(data)))
            else:
                # The expected data is the string representation of the field's
                # native format. To get the value, we will convert the string
                # to data, then back again.
                try:
                    data = result.encode_value(expected_text)
                except fld.FieldDataError, ex:
                    raise self._error(ex)

            value = result.decode_value(data)
            result.constraints.append(Equals(value))
        return result

    def _sequence(self, attributes, children, name, length, breaks):
        value = None
        if attributes.has_key('value'):
            # A sequence can have a value derived from its children...
            value = self._parse_expression(attributes['value'])
        return seq.Sequence(name, children, value, length)

    def _choice(self, attributes, children, name, length, breaks):
        if len(children) == 0:
            raise self._error("Choice '%s' must have children! Should this be a 'reference' entry?" % attributes['name'])
        return chc.Choice(name, children, length)

    def _sequenceof(self, attributes, children, name, length, breaks):
        if len(children) == 0:
            raise self._error("SequenceOf '%s' must have a single child! Should this be a 'reference' entry?" % attributes['name'])
        if len(children) != 1:
            raise self._error("Sequence of entries can only have a single child! (got %i)" % len(children))

        # Default to being a greedy sequenceof, unless we have a length specified
        count = None
        if attributes.has_key('count'):
            count = self._parse_expression(attributes['count'])
        result = sof.SequenceOf(name, children[0], count, length, breaks)
        return result


def load(filename, specfile, references):
    """
    Load an xml specification from a filename or file object.

    xml -- A file object.
    references -- A bdec.spec.references.References instance.

    @return Returns a tuple containing the decoder entry and a dictionary
        of decoder entries to (filename, line number, column number).
    """
    parser = xml.sax.make_parser()
    handler = _Handler(filename, references)
    parser.setContentHandler(handler)
    try:
        parser.parse(specfile)
    except xml.sax.SAXParseException, ex:
        # The sax parse exception object can operate as a locator
        raise XmlError(ex.args[0], filename, ex)
    return (handler.decoder, handler.lookup)

def _save_field(entry, attributes):
    if entry.format is not fld.Field.BINARY:
        attributes += [('type', entry.format)]
    if entry.encoding not in [fld.Field.BIG_ENDIAN, 'ascii']:
        attributes += [('encoding', entry.encoding)]
    return 'field'

def _save_sequence(entry, attributes):
    if entry.length is not None:
        attributes += [('length', str(entry.length))]
    if entry.value is not None:
            attributes += [('value', entry.value)]
    return 'sequence'

def _save_sequenceof(entry, attributes):
    if entry.count is not None:
        attributes += [('count', str(entry.count))]
    if entry.length is not None:
        attributes += [('length', str(entry.length))]
    return 'sequenceof'

def _save_choice(entry, attributes):
    if entry.length is not None:
        attributes += [('length', str(entry.length))]
    return 'choice'

_handlers = {fld.Field: _save_field,
        seq.Sequence: _save_sequence,
        sof.SequenceOf: _save_sequenceof,
        chc.Choice: _save_choice,
        }

class _XmlOut:
    def __init__(self):
        self._buffer  = StringIO.StringIO()
        self._offset = 0
        self._is_open = False

    def __str__(self):
        return self._buffer.getvalue()

    def start(self, name, attributes=()):
        """Mark the start of an xml element.

        name -- The name of the element.
        attributes -- An iterable of (name, value) tuples. If the 'value'
            is None, the pair will be ignored.
        """
        if self._is_open:
            self._buffer.write('>\n')
        self._is_open = True

        self._buffer.write(' ' * self._offset)
        self._buffer.write('<%s' % saxutils.escape(name))

        for name, value in attributes:
            if value is not None:
                name = saxutils.escape(name)
                value = saxutils.escape(str(value))
                self._buffer.write(' %s="%s"' % (name, value))

        self._offset += 4

    def end(self, name):
        self._offset -= 4
        if self._is_open:
            self._buffer.write(' />\n')
        else:
            self._buffer.write(' ' * self._offset)
            self._buffer.write('</%s>\n' % saxutils.escape(name))
        self._is_open = False

def _write_reference(gen, child):
    attributes = [('name', child.name)]
    if child.entry.name != child.name:
        attributes += [('type', child.entry.name)]
    gen.start('reference', attributes)
    gen.end('reference')

def _write_entry(gen, entry, common, end_entry):
    attributes = []
    if entry.name:
        attributes.append(('name', entry.name))
    name = _handlers[type(entry)](entry, attributes)
    if entry.length is not None:
	attributes.append(('length', str(entry.length)))
    for constraint in entry.constraints:
        if isinstance(constraint, Minimum):
            attributes.append(('min', str(constraint.limit)))
        elif isinstance(constraint, Maximum):
            attributes.append(('max', str(constraint.limit)))
        elif isinstance(constraint, Equals):
            value = constraint.limit
            if isinstance(constraint.limit, dt.Data):
                if len(value) % 8:
                    # We can only convert bytes to hex, so added a '0' data
                    # object in front.
                    leading_bits = 8 - len(entry.expected) % 8
                    value = dt.Data('\x00', start=0, end=leading_bits) + value
                value = '0x%s' % value.get_hex()
            # Field entries expected values currently have a different name...
            if isinstance(entry, fld.Field):
                attributes.append(('value', value))
            else:
                attributes.append(('expected', value))
        elif isinstance(constraint, NotEquals):
            attributes.append(('not_equal', str(constraint.limit)))
        else:
            raise NotImplementedError("Don't know how to save contraint '%s'!" % constraint)

    gen.start(name, attributes)
    for child in entry.children:
        if child.entry in common:
            _write_reference(gen, child)
        else:
            _write_entry(gen, child.entry, common, end_entry)

    if end_entry.is_end_sequenceof(entry):
        gen.start('end-sequenceof')
        gen.end('end-sequenceof')
    gen.end(name)

def save(spec, common=[]):
    """Save a specification in the xml format."""
    if spec not in common:
        common = common + [spec]
    end_entry = prm.EndEntryParameters(common)
    gen = _XmlOut()

    gen.start('protocol')
    _write_entry(gen, spec, common, end_entry)
    if len(common) > 1:
        # Only generate common entries when we have something other then the
        # main protocol entry.
        gen.start('common')
        for entry in common:
            if entry is not spec:
                _write_entry(gen, entry, common, end_entry)
        gen.end('common')
    gen.end('protocol')
    return str(gen)

