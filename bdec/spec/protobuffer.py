
from bdec.constraints import Equals
from bdec.field import Field
from bdec.entry import Child
from bdec.expression import parse
from bdec.sequence import Sequence
import bdec.spec.xmlspec
import os.path
from pyparsing import alphanums, Literal, nums, OneOrMore, ParseException, StringEnd, Word

class _Locator:
    def __init__(self, lineno, column):
        self._lineno = lineno
        self._column = column

    def getLineNumber(self):
        return self._lineno

    def getColumnNumber(self):
        return self._column

class Error(bdec.spec.LoadErrorWithLocation):
    def __init__(self, filename, lineno, col, message):
        bdec.spec.LoadErrorWithLocation.__init__(filename, _Locator(lineno, col))
        self._message = message

    def __str__(self):
        return self._src() + self._message

class _Parser:
    def __init__(self, references):
        rule = Literal('required') | 'optional' | 'repeated'
        type = rule + Word(alphanums) + Word(alphanums) + '=' + Word(nums) + ';'
        message = 'message' + Word(alphanums) + '{' + OneOrMore(type) + '}'
        self._parser = OneOrMore(message) + StringEnd()

        type.addParseAction(lambda s,l,t: self._createType(t[0], t[1], t[2], int(t[4])))
        message.addParseAction(lambda s,l,t:self._createMessage(t[1], t[3:-1]))

        self._references = references

    def _createType(self, rule, type, name, fieldNumber):
        if rule != 'required':
            raise NotImplementedError('Only handle required at the moment!')
        entries = []
        if type in ['int32', 'int64', 'uint32', 'uint64', 'sint32', 'sint64',
                'bool', 'enum']:
            wire_type = 0
        elif type in ['fixed64', 'sfixed64', 'double']:
            wire_type = 1
        elif type in ['fixed32', 'sfixed32', 'float']:
            wire_type = 5
        else:
            entries += [Child('length:', self._references.get_common('varint'))]
            wire_type = 2

        if type in ['string', 'bytes']:
            entries += [Field(name, length=parse('${length:} * 8'), format=Field.TEXT)]
        else:
            entries += [Child(name, self._references.get_common(type))]

        keyValue = fieldNumber << 3 | wire_type
        key = Sequence('key:', [self._references.get_common('varint')],
                value=parse("${varint}"), constraints=[Equals(keyValue)])
        return [key] + entries

    def _createMessage(self, name, types):
        return Sequence(name, types)

    def parse(self, text):
        return list(self._parser.parseString(text))

def load(filename, contents, references):
    """Load a protocol buffer spec.

    filename -- The filename of the specification.
    contents -- The protocol buffer specification in a string.
    references -- A bdec.spec.refernce.References instance.
    return -- A tuple of (decoder, lookup).
    """
    # Load the parts of protocol buffers implemented in bdec
    proto_filename = os.path.join(os.path.dirname(__file__), '..', '..', 'specs', 'protobuffer.xml')
    generic_spec, lookup = bdec.spec.xmlspec.load(proto_filename, file(proto_filename, 'r'), references)

    parser = _Parser(references)
    try:
        entries = parser.parse(contents.read())
    except ParseException, ex:
        raise Error(filename, ex.lineno, ex.col, ex)
    for entry in entries:
        references.add_common(entry)
    return entries[0], lookup

