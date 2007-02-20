import StringIO
import xml.sax

import dcdr.choice as chc
import dcdr.data as dt
import dcdr.field as fld
import dcdr.load
import dcdr.sequence as seq
import dcdr.sequenceof as sof

class _Handler(xml.sax.handler.ContentHandler):
    """
    A sax style xml handler for building a decoder from an xml specification
    """
    def __init__(self):
        self._stack = []
        self._children = []

        self._handlers = {
            "choice" : self._choice,
            "field" : self._field,
            "protocol" : self._protocol,
            "sequence" : self._sequence,
            "sequenceof" : self._sequenceof,
            }
        self.decoder = None

    def setDocumentLocator(self, locator):
        self._locator = locator

    def startElement(self, name, attrs):
        if name not in self._handlers:
            raise dcdr.load.LoadError("Unrecognised element '%s'!" % name)

        self._stack.append((name, attrs))
        self._children.append([])

    def endElement(self, name):
        assert self._stack[-1][0] == name
        (name, attrs) = self._stack.pop()

        children = self._children.pop()
        child = self._handlers[name](attrs, children)
        if len(self._children) > 0:
            self._children[-1].append(child)

    def _protocol(self, attributes, children):
        if len(children) != 1:
            raise xml.load.LoadError("Protocol should have a single entry to be decoded!")
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
            expected = dt.Data.from_hex(attributes['value'])
        return fld.Field(name, lambda: length, format, encoding, expected)

    def _sequence(self, attributes, children):
        return seq.Sequence(attributes['name'], children)

    def _choice(self, attributes, children):
        return chc.Choice(attributes['name'], children)

    def _sequenceof(self, attributes, children):
        if len(children) != 1:
            raise dcdr.load.LoadError("Sequence of entries can only have a single child! (got %i)" % len(children))
        length = int(attributes['length'])
        return sof.SequenceOf(attributes['name'], children[0], lambda: length)

class Importer:
    """
    Class to create a decoder from an xml specification
    """

    def loads(self, xml):
        """
        Parse an xml data stream, interpreting it as a protocol
        specification.
        """
        return self.load(StringIO.StringIO(xml))

    def load(self, file):
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
