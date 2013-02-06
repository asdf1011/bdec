
from bdec.constraints import Equals
from bdec.entry import Child
from bdec.expression import parse
from bdec.sequence import Sequence
import bdec.spec.xmlspec
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

_var_int = None
def _createVarInt():
    """ Create an decoder for variable integers. """
    global _var_int
    if not _var_int:
        spec = '''
          <protocol>
            <reference name="varint" />
            <common>
              <sequence name="varint" value="${embedded:}" >
                <choice name="embedded:">
                  <sequence name="single byte" value="${value}">
                    <field length="1" value="0" />
                    <field name="value" length="7" type="integer" />
                  </sequence>
                  <sequence name="multi byte" value="${varint} * 128 + ${value}" >
                    <field length="1" value="1" />
                    <field name="value" length="7" type="integer" />
                    <reference name="varint" />
                  </sequence>
                </choice>
              </sequence>
            </common>
          </protocol>
          '''
        _var_int = bdec.spec.load_specs([('varint.xml', spec, None)])[0]
    return _var_int

def _create_int32(name):
    return 0, Sequence(name, [Child('value:', _createVarInt())], value=parse("${value:}"))

# A lookup of type name to handling function. The handing function takes
# the name and returns a (entry, typeNumber) tuple.
_type_lookup = {'int32' : _create_int32}

def _createType(rule, type, name, fieldNumber):
    if rule != 'required':
        raise Exception('Only handlle required at the moment!')
    wire_type, entry = _type_lookup[type](name)

    keyValue = fieldNumber << 3 | wire_type
    key = Sequence('key:', [_createVarInt()], value=parse("${varint}"), constraints=[Equals(keyValue)])
    return [key, entry]

def _createMessage(name, types):
    return Sequence(name, types)

def loads(text, filename=None):
    """Load a protocol buffer spec from a string.

    text -- The protocol buffer specification in a string.
    filename -- The filename of the specification.
    return -- A tuple of (messages, common, lookup), where messages is a list of
        bdec.entry.Entry instances.
    """
    rule = Literal('required') | 'optional' | 'repeated'
    type = rule + Word(alphanums) + Word(alphanums) + '=' + Word(nums) + ';'
    message = 'message' + Word(alphanums) + '{' + OneOrMore(type) + '}'
    complete = OneOrMore(message) + StringEnd()

    type.addParseAction(lambda s,l,t: _createType(t[0], t[1], t[2], int(t[4])))
    message.addParseAction(lambda s,l,t: _createMessage(t[1], t[3:-1]))

    try:
        entries = list(complete.parseString(text))
    except ParseException, ex:
        raise Error(filename, ex.lineno, ex.col, ex)
    return entries, entries + [_createVarInt()], {}

def load(file):
    """Load a protocol buffer spec from a file.

    file -- Either a filename, or a file type object.
    """
    filename = None
    if isinstance(file, basestring):
        filename = file
        file = load(filename, 'rb')
    return loads(file.read(), filename)

