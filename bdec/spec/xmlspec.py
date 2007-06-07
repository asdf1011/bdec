import StringIO
import xml.sax

import bdec.choice as chc
import bdec.data as dt
import bdec.field as fld
import bdec.spec
import bdec.sequence as seq
import bdec.sequenceof as sof

class XmlSpecError(bdec.spec.LoadError):
    pass

class _Handler(xml.sax.handler.ContentHandler):
    """
    A sax style xml handler for building a decoder from an xml specification
    """
    def __init__(self):
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

    def setDocumentLocator(self, locator):
        self._locator = locator

    def startElement(self, name, attrs):
        if name not in self._handlers:
            raise XmlSpecError("Unrecognised element '%s'!" % name)

        self._stack.append((name, attrs))
        self._children.append([])

    def endElement(self, name):
        assert self._stack[-1][0] == name
        (name, attrs) = self._stack.pop()

        children = self._children.pop()
        if attrs.has_key('name') and attrs.getValue('name') in self._common_entries:
            # We are referencing to a common element...
            if len(attrs) != 1:
                raise XmlSpecError("Referenced element '%s' cannot have other attributes!" % attrs['name'])
            if len(children) != 0:
                raise XmlSpecError("Referenced element '%s' cannot have sub-entries!" % attrs['name'])
            child = self._common_entries[attrs['name']]
        else:
            child = self._handlers[name](attrs, children)

        if child is not None:
            self._children[-1].append(child)

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
            raise XmlSpecError("Protocol should have a single entry to be decoded!")
        self.decoder = children[0]

    def _field(self, attributes, children):
        name = attributes['name']
        length = int(attributes['length'])
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
        return seq.Sequence(attributes['name'], children)

    def _choice(self, attributes, children):
        return chc.Choice(attributes['name'], children)

    def _sequenceof(self, attributes, children):
        if len(children) != 1:
            raise XmlSpecError("Sequence of entries can only have a single child! (got %i)" % len(children))
        length = int(attributes['length'])
        return sof.SequenceOf(attributes['name'], children[0], length)

def _load_from_file(file):
    """
    Read a string from open file and interpret it as an
    xml data stream identifying a protocol entity.

    @return Returns a decoder entry.
    """
    parser = xml.sax.make_parser()
    handler = _Handler()
    parser.setContentHandler(handler)
    parser.parse(file)
    return handler.decoder

def loads(xml):
    """
    Parse an xml string, interpreting it as a protocol specification.
    """
    return _load_from_file(StringIO.StringIO(xml))

def load(xml):
    """
    Load an xml specification from a filename or file object.
    """
    if isinstance(xml, basestring):
        xml = open(xml, "r")
        result = _load_from_file(xml)
        xml.close()
    else:
        result = _load_from_file(xml)
    return result
