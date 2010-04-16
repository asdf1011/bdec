
import inspect
from string import ascii_letters as alphas, digits as nums, hexdigits as hexnums, printable as printables

from bdec import DecodeError
from bdec.choice import Choice
from bdec.constraints import Equals, NotEquals
from bdec.data import Data
from bdec.entry import is_hidden
from bdec.expression import LengthResult, ValueResult
from bdec.field import Field
from bdec.sequence import Sequence
from bdec.sequenceof import SequenceOf
from bdec.spec.references import ReferencedEntry

alphanums = alphas + nums

class ParseException(DecodeError):
    def __init__(self, filename, text, offset, ex):
        DecodeError.__init__(self, ex.entry)
        self._filename = filename
        self._text = text
        self._offset = offset
        self.error = ex

    @property
    def _lines(self):
        return self._text[:self._offset / 8].splitlines() or ['']

    @property
    def lineno(self):
        return len(self._lines)

    @property
    def col(self):
        return len(self._lines[-1])

    def __str__(self):
        return '%s[%i]: %s\n%s\n%s' % (self._filename, self.lineno,
                str(self.error), self._text.splitlines()[self.lineno-1],
                ' ' * self.col + '^')


class ParserElement:
    def __init__(self):
        self._actions = []
        self._internal_actions = []
        self._am_resolving = False

        # The parser includes leading whitespace, the decoder doesn't.
        self._parser = None
        self._decoder = None
        self._ignore = None

    def _is_important(self):
        return self._actions or self._internal_actions or self._ignore

    def ignore(self, expr):
        self._ignore = expr

    def _createEntry(self, separator):
        raise NotImplementedError()

    def createDecoder(self, separator):

        if self._decoder is not None:
            return self._decoder

        if self._am_resolving:
            self._references.append(ReferencedEntry('forward', 'forward'))
            return self._references[-1]

        if self._ignore is not None:
            separator = separator | self._ignore

        # It is possible (even likely for Forward elements) that we will be
        # referenced while creating the referencing decoder; we handle this
        # by returning ReferencedEntry instances until the decoder has been
        # constructed, then resolve them all.
        self._am_resolving = True
        self._references = []
        self._decoder = self._createEntry(separator)
        for reference in self._references:
            reference.resolve(self._decoder)

        try:
            self._decoder.actions
        except AttributeError:
            self._decoder.actions = []
        self._decoder.actions += self._internal_actions + self._actions
        return self._decoder

    def setParseAction(self, fn):
        self._actions = []
        return self.addParseAction(fn)

    def addParseAction(self, fn):
        num_args = len(inspect.getargspec(fn)[0])
        if num_args == 3:
            action = lambda t:fn('', 0, t)
        elif num_args == 2:
            action = lambda t:fn(0, t)
        else:
            action = fn

        self._actions.append(action)
        return self

    def parseString(self, text):
        if isinstance(text, unicode):
            text = text.encode('ascii')

        stack = []
        tokens = []
        for is_starting, name, entry, data, value in self._decode(text, '<string>'):
            if is_starting:
                stack.append(tokens)
                tokens = []
            else:
                if name and not is_hidden(name) and value is not None:
                    tokens.append(value)

                try:
                    actions = entry.actions
                except AttributeError:
                    actions = []

                for action in actions:
                    tokens = action(tokens)
                    if not isinstance(tokens, list):
                        tokens = [tokens]

                # Extend the current tokens list with the child tokens
                stack[-1].extend(tokens)
                tokens = stack.pop()
        assert len(stack) == 0
        return tokens

    def _decode(self, text, filename):
        if self._parser is None:
            whitespace = Word(' \n')
            if self._ignore is not None:
                whitespace = whitespace | self._ignore
            whitespace = Suppress(ZeroOrMore(whitespace))

            # Whitespace is decoded at the end of the Literal (and Word) entries,
            # so we have to decode any leading whitespace. The alternative,
            # decoding the whitespace before Literal (and Word) entries, would
            # prevent the Chooser from being able to guess the type.
            self._parser = Sequence(None, [whitespace.createDecoder(None),
                self.createDecoder(whitespace)])

        offset = 0
        try:
            for is_starting, name, entry, data, value in self._parser.decode(Data(text)):
                if not is_starting:
                    offset += len(data)
                yield is_starting, name, entry, data, value
        except DecodeError, ex:
            raise ParseException(filename, text, offset, ex)

    def __add__(self, other):
        if not isinstance(other, ParserElement):
            other = Literal(other)
        return And([self, other])

    def __radd__(self, other):
        if not isinstance(other, ParserElement):
            other = Literal(other)
        return And([other, self])

    def __or__(self, other):
        return MatchFirst([self, other])

    def __ror__(self, other):
        if not isinstance(other, ParserElement):
            other = Literal(other)
        return MatchFirst([other, self])


class ZeroOrMore(ParserElement):
    def __init__(self, element):
        ParserElement.__init__(self)
        self.element = element

    def _createEntry(self, separator):
        entry = self.element.createDecoder(separator)
        end = Sequence(None, [])
        item = Choice('item', [entry, end])
        return SequenceOf('items', item, end_entries=[end])

    def __str__(self):
        return '{%s}' % self.element


class OneOrMore(ParserElement):
    def __init__(self, element):
        ParserElement.__init__(self)
        self.element = element

    def _createEntry(self, separator):
        element = (self.element + ZeroOrMore(self.element))
        return element.createDecoder(separator)

    def __str__(self):
        return '%s, {%s}' % (self.element, self.element)


class Literal(ParserElement):
    def __init__(self, text):
        ParserElement.__init__(self)
        assert isinstance(text, basestring), 'Literal must be a string! Is %s' % (repr(text))
        self.text = text

    def _createEntry(self, separator):
        result = Field('literal', length=len(self.text) * 8, format=Field.TEXT, constraints=[Equals(self.text)])
        if separator:
            result = Sequence('literal', [result, separator.createDecoder(None)])
        return result

    def __str__(self):
        return '"%s"' % repr(self.text)[1:-1]


class Word(ParserElement):
    def __init__(self, chars):
        ParserElement.__init__(self)
        self.chars = chars

    def _element(self):
        return OneOrMore(MatchFirst([Literal(c) for c in self.chars]))

    def _createEntry(self, separator):
        entry = self._element().createDecoder(None)
        self._internal_actions.append(lambda t: [''.join(t)])
        if separator:
            entry = Sequence('word', [entry, separator.createDecoder(None)])
        return entry

    def __str__(self):
        return str(self._element())

def _check_literals(exprs):
    result = []
    for expr in exprs:
        if not isinstance(expr, ParserElement):
            result.append(Literal(expr))
        else:
            result.append(expr)
    return result

class And(ParserElement):
    def __init__(self, exprs):
        ParserElement.__init__(self)
        self.exprs = _check_literals(exprs)

    def _createEntry(self, separator):
        return Sequence('and', [e.createDecoder(separator) for e in self.exprs])

    def __add__(self, other):
        if not isinstance(other, ParserElement):
            other = Literal(other)

        if self._is_important():
            return ParserElement.__add__(self, other)
        return And(self.exprs + [other])

    def __radd__(self, other):
        if self._is_important():
            return ParserElement.__radd__(self, other)
        return And([Literal(other)] + self.exprs)

    def __str__(self):
        return '(%s)' % ', '.join(str(e) for e in self.exprs)


class MatchFirst(ParserElement):
    def __init__(self, exprs):
        ParserElement.__init__(self)
        self.exprs = _check_literals(exprs)

    def _createEntry(self, separator):
        return Choice('or', [e.createDecoder(separator) for e in self.exprs])

    def __str__(self):
        return '[%s]' % (', '.join(str(e) for e in self.exprs))

    def __or__(self, other):
        if not isinstance(other, ParserElement):
            other = Literal(other)

        if self._is_important():
            return ParserElement.__or__(self, other)
        return MatchFirst(self.exprs + [other])

    def __ror__(self, other):
        if self._is_important():
            return ParserElement.__ror__(self, other)
        return MatchFirst([Literal(other)] + self.exprs)

# In pyparsing this means 'match the longest entry'; we don't do that, so
# just pretend it's the same as MatchFirst.
Or = MatchFirst

class StringEnd(ParserElement):
    def _createEntry(self, separator):
        data = Choice('data:', [Field(None, length=8), Sequence(None, [])])
        length_check = Sequence(None, [], value=LengthResult('data:'), constraints=[Equals(0)])
        return Sequence(None, [data, length_check])


class NoMatch(ParserElement):
    def _createEntry(self, separator):
        return Sequence(None, [], value=Constant(0), constraints=[Equals(1)])


class CharsNotIn(ParserElement):
    def __init__(self, notChars):
        ParserElement.__init__(self)
        self.notChars = notChars

    def _createEntry(self, separator):
        checks = []
        for c in self.notChars:
            checks.append(Sequence(None, [], value=ValueResult('char not in'),
                    constraints=[NotEquals(ord(c))]))
        good_char = Sequence('good char', [Field('char not in', length=8, format=Field.INTEGER)] + checks)
        end = Sequence(None, [])
        char = Choice('test char', [good_char, end])
        entry = SequenceOf('chars not in', char, end_entries=[end])

        def joinCharacters(toks):
            if toks:
                return [''.join(chr(t) for t in toks)]
            return []
        self._internal_actions.append(joinCharacters)

        children = [good_char, entry]
        if separator:
            children.append(separator.createDecoder(None))
        result = Sequence('chars not in', children)
        return result

    def __str__(self):
        return '[not in %s]' % repr(self.notChars)


class Suppress(ParserElement):
    def __init__(self, expr):
        ParserElement.__init__(self)
        if not isinstance(expr, ParserElement):
            expr = Literal(expr)
        self.expr = expr
        self._internal_actions.append(lambda toks:[])

    def _createEntry(self, separator):
        return self.expr.createDecoder(separator)


class Forward(ParserElement):
    def __init__(self):
        ParserElement.__init__(self)
        self.element = None

    def __lshift__(self, expr):
        if not isinstance(expr, ParserElement):
            expr = Literal(expr)
        self.element = expr

    def _createEntry(self, separator):
        assert self.element is not None
        return self.element.createDecoder(separator)

class Combine(ParserElement):
    def __init__(self, expr):
        ParserElement.__init__(self)
        self.expr = expr

        def joinTokens(toks):
            if toks:
                return [''.join(t for t in toks)]
            return []
        self._internal_actions.append(joinTokens)

    def _createEntry(self, separator):
        return self.expr.createDecoder(None)

def srange(text):
    assert text[0] == '[' and text[-1] == ']'
    text = text[1:-1]
    chars = ''
    while text:
        if len(text) > 2 and text[1] == '-':
            chars += ''.join(chr(i) for i in range(ord(text[0]), ord(text[2])+1))
            text = text[3:]
        else:
            chars += text[0]
            text = text[1:]
    return chars

class CaselessLiteral(ParserElement):
    def __init__(self, text):
        ParserElement.__init__(self)
        self.text = text
        self._internal_actions.append(self._toCase)

    def _toCase(self, toks):
        if self.text[0].isupper():
            return [toks[0].upper()]
        else:
            return [toks[0].lower()]

    def _createEntry(self, separator):
        chars = ((Literal(c.lower()) | Literal(c.upper())) for c in self.text)
        element = Combine(reduce(lambda a,b:a+b, chars))
        return element.createDecoder(None)

