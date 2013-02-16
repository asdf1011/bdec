
from bdec.choice import Choice
from bdec.constraints import Equals
from bdec.field import Field
from bdec.entry import Child
from bdec.expression import parse
from bdec.sequence import Sequence
from bdec.sequenceof import SequenceOf
import bdec.spec.xmlspec
import os.path
from pyparsing import alphanums, Literal, nums, OneOrMore, ParseException, \
        StringEnd, Word, Optional, SkipTo

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
        bdec.spec.LoadErrorWithLocation.__init__(self, filename, _Locator(lineno, col))
        self._message = message

    def __str__(self):
        return '%s %s' % (self._src(), self._message)

class _Parser:
    def __init__(self, references):
        rule = Literal('required') | 'optional' | 'repeated'
        packed = Optional('[packed=true]').addParseAction(lambda s,l,t: t[0] if t else '')
        type = rule + Word(alphanums) + Word(alphanums) + '=' + Word(nums) + packed + ';'
        enum_option = Word(alphanums) + '=' + Word(nums) + ';'
        enum = 'enum' + Word(alphanums) + '{' + OneOrMore(enum_option) + '}'
        message = 'message' + Word(alphanums) + '{' + OneOrMore(enum | type) + '}'
        self._parser = OneOrMore(message) + StringEnd()

        comment = '//' + SkipTo('\n')
        self._parser.ignore(comment)

        type.addParseAction(lambda s,l,t: self._createType(t[0], t[1], t[2], int(t[4]), t[5]))
        enum_option.addParseAction(lambda s,l,t: self._create_option(t[0], t[2]))
        enum.addParseAction(lambda s,l,t: self._create_enum(t[1], t[3:-1]))
        message.addParseAction(lambda s,l,t:self._createMessage(t[1], t[3:-1]))

        self._references = references
        self._enum_types = set()

    def _create_option(self, name, value):
        return Sequence(name,
                [Child('value:', self._references.get_common('varint'))],
                value=parse('${value:}'), constraints=[Equals(int(value))])

    def _create_enum(self, name, options):
        self._enum_types.add(name)
        self._references.add_common(Choice(name, options))
        return []

    def _createType(self, rule, type, name, fieldNumber, packed):
        length = []
        if type in ['int32', 'int64', 'uint32', 'uint64', 'sint32', 'sint64',
                'bool', 'enum'] or type in self._enum_types:
            wire_type = 0
        elif type in ['fixed64', 'sfixed64', 'double']:
            wire_type = 1
        elif type in ['fixed32', 'sfixed32', 'float']:
            wire_type = 5
        else:
            length = [Child('length:', self._references.get_common('varint'))]
            wire_type = 2

        keyValue = fieldNumber << 3 | wire_type
        key = [Sequence('key:', [self._references.get_common('varint')],
                value=parse("${varint}"), constraints=[Equals(keyValue)])]

        if type in ['string', 'bytes']:
            entry = Field(name, length=parse('${length:} * 8'), format=Field.TEXT, encoding="utf8")
        else:
            entry = Child(name, self._references.get_common(type))


        if rule != 'repeated' and packed:
            raise NotImplementedError("Found a packed entry that isn't repeated?!")

        if rule == 'required':
            result = key + length + [entry]
        elif rule == 'optional':
            check = Choice('%s check:' % name, [
                Sequence('present', key, value=parse("1")),
                Sequence('not present', [Sequence('length:', [], value=parse("0"))], value=parse("0"))])
            if length:
                length = [Choice('length:', [
                    Sequence('not present', [
                        Sequence('check:', [], value=parse("${%s check:}" % name), constraints=[Equals(0)])],
                        value=parse('0')),
                    length[0]])]
            result = [check] + length + [Choice('optional %s' % name, [
                Sequence('not present:', [], value=parse("${%s check:}" % name), constraints=[Equals(0)]),
                entry])]
        elif rule == 'repeated':
            # This is a little awkward, as we have to create an additional
            # sequence to pack in the hidden key / length.
            if not packed:
                result = [SequenceOf(name, Sequence(name, key + length + [entry]))]
            else:
                result = key + length + [SequenceOf(name,
                    Sequence(name, length + [entry]),
                    length=parse("${length:} * 8"))]
        else:
            raise NotImplementedError("Unhandled rule '%s'" % rule)

        return result

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
    return entries[-1], lookup

