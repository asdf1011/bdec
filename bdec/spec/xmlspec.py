import StringIO
import xml.sax

import bdec.choice as chc
import bdec.data as dt
import bdec.field as fld
import bdec.spec
import bdec.sequence as seq
import bdec.sequenceof as sof
import bdec.spec.expression as exp

class XmlSpecError(bdec.spec.LoadError):
    def __init__(self, filename, locator):
        self.filename = filename
        self.line = locator.getLineNumber()
        self.column = locator.getColumnNumber()

    def _src(self):
        return "%s[%s]: " % (self.filename, self.line)

class XmlError(XmlSpecError):
    """
    Class for some common xml specification errors.
    """
    def __init__(self, error, filename, locator):
        XmlSpecError.__init__(self, filename, locator)
        self.error = error

    def __str__(self):
        return self._src() + str(self.error)

class EmptySequenceError(XmlSpecError):
    def __init__(self, name, filename, locator):
        XmlSpecError.__init__(self, filename, locator)
        self.name = name

    def __str__(self):
        return self._src() + "Sequence '%s' must have children!" % self.name

class NonFieldError(exp.ExpressionError):
    def __init__(self, entry):
        self.entry = entry

    def __str__(self):
        return "Expression can only reference fields (%s)" % self.entry

class NonSequenceError(exp.ExpressionError):
    """
    Asked for a child of a non-sequence object.
    """
    def __init__(self, entry):
        self.entry = entry

    def __str__(self):
        return "Expressions can only reference children of sequences (%s)" % self.entry

class MissingReferenceError(exp.ExpressionError):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "Expression references unknown field '%s'" % self.name

class XmlExpressionError(XmlSpecError):
    def __init__(self, ex, filename, locator):
        XmlSpecError.__init__(self, filename, locator)
        self.ex = ex

    def __str__(self):
        return self._src() + "Expression error - " + str(self.ex)

class _FieldResult:
    """
    Object returning the result of a field when cast to an integer.
    """
    def __init__(self):
        self.length = None

    def add_field(self, field):
        field.add_listener(self)

    def __call__(self, field):
        self.length = int(field)

    def __int__(self):
        assert self.length is not None
        return self.length

class _Handler(xml.sax.handler.ContentHandler):
    """
    A sax style xml handler for building a decoder from an xml specification
    """
    def __init__(self, filename):
        self._filename = filename
        self._stack = []
        self._children = []

        self._handlers = {
            "common" : self._common,
            "choice" : self._choice,
            "field" : self._field,
            "protocol" : self._protocol,
            "sequence" : self._sequence,
            "sequenceof" : self._sequenceof,
            }
        self.decoder = None
        self._common_entries = {}

        self.lookup = {}
        self.locator = None

    def setDocumentLocator(self, locator):
        self.locator = locator

    def _error(self, text):
        return XmlError(text, self._filename, self.locator)

    def startElement(self, name, attrs):
        if name not in self._handlers:
            raise self._error("Unrecognised element '%s'!" % name)

        self._stack.append((name, attrs))
        self._children.append([])

    def endElement(self, name):
        assert self._stack[-1][0] == name
        (name, attrs) = self._stack.pop()

        children = self._children.pop()
        if attrs.has_key('name') and attrs.getValue('name') in self._common_entries:
            # We are referencing to a common element...
            if len(attrs) != 1:
                raise self._error("Referenced element '%s' cannot have other attributes!" % attrs['name'])
            if len(children) != 0:
                raise self._error("Referenced element '%s' cannot have sub-entries!" % attrs['name'])
            child = self._common_entries[attrs['name']]
        else:
            child = self._handlers[name](attrs, children)

        if child is not None:
            self._children[-1].append(child)

            self.lookup[child] = (self._filename, self.locator.getLineNumber(), self.locator.getColumnNumber())

        if len(self._stack) == 2 and self._stack[1][0] == 'common':
            # We have to handle common entries _before_ the end of the
            # 'common' element, as common entries can reference other
            # common entries.
            assert child is not None
            self._common_entries[child.name] = child

    def _common(self, attributes, children):
        pass

    def _protocol(self, attributes, children):
        if len(children) != 1:
            raise self._error("Protocol should have a single entry to be decoded!")
        self.decoder = children[0]

    def _decode_length(self, text):
        try:
            return exp.compile(text, self._query_field)
        except exp.ExpressionError, ex:
            raise XmlExpressionError(ex, self._filename, self.locator)

    def _query_field(self, fullname):
        """
        Get an object that returns the decoded value of a field.

        The fullname is the qualified name of the entry with respect to
        the current entry.
        """
        names = fullname.split('.')

        # Find the first name by walking up the stack
        for children in reversed(self._children):
            for entry in reversed(children):
                if entry.name == names[0]:
                    # We've found the top-level name; now drill down until
                    # we find the child.
                    for name in names[1:]:
                        if not isinstance(entry, seq.Sequence):
                            # TODO: It can be useful to be able to look inside
                            # a choice (for example, with fields with a variable
                            # sized length).
                            raise NonSequenceError(fullname)

                        for child in entry.children:
                            if child.name == name:
                                entry = child
                                break
                        else:
                            raise MissingReferenceError(fullname)

                    if not isinstance(entry, fld.Field):
                        raise NonFieldError(entry)

                    result = _FieldResult()
                    result.add_field(entry)
                    return result
        raise MissingReferenceError(name)

    def _field(self, attributes, children):
        name = attributes['name']
        length = self._decode_length(attributes['length'])
        format = fld.Field.BINARY
        if attributes.has_key('type'):
            lookup = {
                "binary" : fld.Field.BINARY,
                "hex" : fld.Field.HEX,
                "integer" : fld.Field.INTEGER,
                "text" : fld.Field.TEXT,
                }
            format = lookup[attributes['type']]
        encoding = None
        if attributes.has_key('encoding'):
            encoding = attributes['encoding']
        expected = None
        if attributes.has_key('value'):
            hex = attributes['value'].upper()
            assert hex[:2] == "0X"
            expected = dt.Data.from_hex(hex[2:])
        return fld.Field(name, length, format, encoding, expected)

    def _sequence(self, attributes, children):
        if len(children) == 0:
            raise EmptySequenceError(attributes['name'], self._filename, self.locator)
        return seq.Sequence(attributes['name'], children)

    def _choice(self, attributes, children):
        return chc.Choice(attributes['name'], children)

    def _sequenceof(self, attributes, children):
        if len(children) != 1:
            raise self._error("Sequence of entries can only have a single child! (got %i)" % len(children))

        # Default to being a greedy sequenceof, unless we have a length specified
        length = None
        if attributes.has_key('length'):
            length = self._decode_length(attributes['length'])
        return sof.SequenceOf(attributes['name'], children[0], length)

def _load_from_file(file, filename):
    """
    Read a string from open file and interpret it as an
    xml data stream identifying a protocol entity.

    @return Returns a tuple containing the decoder entry, and a dictionary
        of decoder entries to (filename, line number, column number)
    """
    parser = xml.sax.make_parser()
    handler = _Handler(filename)
    parser.setContentHandler(handler)
    try:
        parser.parse(file)
    except xml.sax.SAXParseException, ex:
        # The sax parse exception object can operate as a locator
        raise XmlError(ex.args[0], filename, ex)
    return (handler.decoder, handler.lookup)

def loads(xml):
    """
    Parse an xml string, interpreting it as a protocol specification.
    """
    return _load_from_file(StringIO.StringIO(xml), "<string>")

def load(xml):
    """
    Load an xml specification from a filename or file object.
    """
    if isinstance(xml, basestring):
        xmlfile = open(xml, "r")
        result = _load_from_file(xmlfile, xml)
        xmlfile.close()
    else:
        result = _load_from_file(xml, "<stream>")
    return result
