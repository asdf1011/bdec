import pickle
import StringIO
import xml.sax

import bdec.choice as chc
import bdec.data as dt
import bdec.entry as ent
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

class MissingReferenceError(exp.ExpressionError):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "Expression references unknown field '%s'" % self.name

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
        return self._src() + "Expression error - " + str(self.ex)

class _ValueResult:
    """
    Object returning the result of a entry when cast to an integer.
    """
    def __init__(self):
        self.length = None

    def add_entry(self, entry):
        entry.add_listener(self)

    def __call__(self, entry, length):
        if isinstance(entry, fld.Field):
            self.length = int(entry)
        elif isinstance(entry, seq.Sequence):
            self.length = int(entry.value)
        else:
            raise Exception("Don't know how to get the result of %s" % entry)

    def __int__(self):
        assert self.length is not None
        return self.length

class _LengthResult:
    """
    Object returning the length of a decoded entry.
    """
    def __init__(self, entries):
        for entry in entries:
            entry.add_listener(self)
        self.length = None

    def __call__(self, entry, length):
        self.length = length

    def __int__(self):
        assert self.length is not None
        return self.length

class _BreakListener:
    """
    Class to stop a sequenceof when another protocol entry decodes.
    """
    def __init__(self):
        self._seqof = None

    def set_sequenceof(self, sequenceof):
        assert self._seqof is None
        assert isinstance(sequenceof, sof.SequenceOf)
        self._seqof = sequenceof

    def __call__(self, entry, length):
        assert self._seqof is not None
        self._seqof.stop()

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
            "end-sequenceof" : self._break,
            "field" : self._field,
            "protocol" : self._protocol,
            "sequence" : self._sequence,
            "sequenceof" : self._sequenceof,
            }
        self.decoder = None
        self._common_entries = {}

        self.lookup = {}
        self.locator = None
        self._end_sequenceof = False
        self._break_listener = None

    def setDocumentLocator(self, locator):
        self.locator = locator

    def _break(self, attrs, children, length):
        if len(attrs) != 0 or len(children) != 0:
            raise self._error("end-sequenceof cannot have attributes or sub-elements")

        assert self._end_sequenceof == False
        self._end_sequenceof = True

    def _error(self, text):
        return XmlError(text, self._filename, self.locator)

    def startElement(self, name, attrs):
        if name not in self._handlers:
            raise self._error("Unrecognised element '%s'!" % name)

        self._stack.append((name, attrs, []))
        self._children.append([])

    def endElement(self, name):
        assert self._stack[-1][0] == name
        (name, attrs, breaks) = self._stack.pop()

        # We don't pop the children item until after we have called the
        # handler, as it may be used when creating a value reference.
        children = self._children[-1]
        if attrs.has_key('name') and attrs.getValue('name') in self._common_entries:
            # We are referencing to a common element...
            if len(attrs) != 1:
                raise self._error("Referenced element '%s' cannot have other attributes!" % attrs['name'])
            if len(children) != 0:
                raise self._error("Referenced element '%s' cannot have sub-entries!" % attrs['name'])

            # There is a problem where listeners to common entries will be
            # called for all common deocdes (see the 
            # test_common_elements_are_independent testcase). We attempt to
            # work around this problem be copying common elements.
            child = pickle.loads(pickle.dumps(self._common_entries[attrs['name']]))
        else:
            length = None
            if attrs.has_key('length'):
                length = self._parse_expression(attrs['length'])
            child = self._handlers[name](attrs, children, length)
        self._children.pop()

        if child is not None:
            for break_notifier in breaks:
                break_notifier.set_sequenceof(child)

            if self._end_sequenceof:
                # There is a parent sequence of object that must stop when
                # this entry decodes.
                listener = _BreakListener()
                child.add_listener(listener)
                for name, attrs, breaks in reversed(self._stack):
                    if name == "sequenceof":
                        breaks.append(listener)
                        break
                else:
                    raise self._error("end-sequenceof is not surrounded by a sequenceof")
                self._end_sequenceof = False
            self._children[-1].append(child)

            self.lookup[child] = (self._filename, self.locator.getLineNumber(), self.locator.getColumnNumber())

        if len(self._stack) == 2 and self._stack[1][0] == 'common':
            # We have to handle common entries _before_ the end of the
            # 'common' element, as common entries can reference other
            # common entries.
            assert child is not None
            self._common_entries[child.name] = child

    def _common(self, attributes, children, length):
        pass

    def _protocol(self, attributes, children, length):
        if len(children) != 1:
            raise self._error("Protocol should have a single entry to be decoded!")
        if self._break_listener is not None:
            raise self._error("end-sequenceof is not surrounded by a sequenceof")
        self.decoder = children[0]

    def _parse_expression(self, text):
        try:
            return exp.compile(text, self._query_entry_value, self._query_length)
        except exp.ExpressionError, ex:
            raise XmlExpressionError(ex, self._filename, self.locator)

    def _get_entry_children(self, entry, name):
        """
        Get an iterator to all children of an entity matching a given
        name.
        """
        if isinstance(entry, seq.Sequence):
            for child in self._get_children(entry.children, name):
                yield child
        elif isinstance(entry, chc.Choice):
            found_name = None
            for option in entry.children:
                option_matches = False
                for child in self._get_children([option], name):
                    option_matches = True
                    yield child

                if found_name is None:
                    found_name = option_matches
                else:
                    if found_name != option_matches:
                        # Not all of the choice entries agree; for some the
                        # name matches, but not for others.
                        if option_matches:
                            # This option has the named entry, but the
                            # previous one didn't.
                            missing = entry.children[entry.children.index(option) - 1]
                        else:
                            missing = option
                        raise OptionMissingNameError(missing, name, self.lookup)

    def _get_children(self, items, name):
        """
        Get an iterator to all children matching the given name.

        There may be more then one in the event children of a 
        'choice' entry are selected.
        """
        for entry in items:
            if name == entry.name:
                yield entry
                return

            if ent.is_hidden(entry.name):
                # If an entry is hidden, look into its children for the name.
                match = False
                for child in self._get_entry_children(entry, name):
                    match = True
                    yield child
                if match:
                    return

    def _query_length(self, fullname):
        """
        Create an object that returns the length of decoded data in an entry.
        """
        return _LengthResult(self._get_entries(fullname))

    def _query_entry_value(self, fullname):
        """
        Get an object that returns the decoded value of a protocol entry.

        The fullname is the qualified name of the entry with respect to
        the current entry. 'Hidden' entries may or may not be included.

        Typically only fields have a value, but sequences may also be assigned
        values.
        """
        result = _ValueResult()
        for entry in self._get_entries(fullname):
            if isinstance(entry, fld.Field):
                result.add_entry(entry)
            elif isinstance(entry, seq.Sequence) and entry.value is not None:
                result.add_entry(entry)
            else:
                raise EntryHasNoValueError(entry)
        return result

    def _get_entries(self, fullname):
        """
        Get a list of all entries that match a given name.
        """
        names = fullname.split('.')

        # Find the first name by walking up the stack
        for children in reversed(self._children):
            matches = list(self._get_children(children, names[0]))
            if matches:
                for name in names[1:]:
                    # We've found items that match the top name. Each of
                    # these items _must_ support the requested names.
                    subitems = [list(self._get_entry_children(child, name)) for child in matches]
                    matches = []
                    for items in subitems:
                        if len(items) == 0:
                            raise MissingReferenceError(name)
                        matches.extend(items)

                return matches
        raise MissingReferenceError(fullname)

    def _field(self, attributes, children, length):
        name = attributes['name']
        format = fld.Field.BINARY
        if length is None:
            raise self._error("Field entries required a 'length' attribute")

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
        min = None
        if attributes.has_key('min'):
            min = self._parse_expression(attributes['min'])
        max = None
        if attributes.has_key('max'):
            max = self._parse_expression(attributes['max'])
        return fld.Field(name, length, format, encoding, expected, min, max)

    def _sequence(self, attributes, children, length):
        if len(children) == 0:
            raise EmptySequenceError(attributes['name'], self._filename, self.locator)
        value = None
        if attributes.has_key('value'):
            # A sequence can have a value derived from its children...
            value = self._parse_expression(attributes['value'])
        return seq.Sequence(attributes['name'], children, value, length)

    def _choice(self, attributes, children, length):
        return chc.Choice(attributes['name'], children, length)

    def _sequenceof(self, attributes, children, length):
        if len(children) != 1:
            raise self._error("Sequence of entries can only have a single child! (got %i)" % len(children))

        # Default to being a greedy sequenceof, unless we have a length specified
        count = None
        if attributes.has_key('count'):
            count = self._parse_expression(attributes['count'])
        result = sof.SequenceOf(attributes['name'], children[0], count, length)

        if self._break_listener is not None:
            self._break_listener.set_sequenceof(result)
            self._break_listener = None
        return result

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
