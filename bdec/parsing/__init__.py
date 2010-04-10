
from string import ascii_letters as alphas, digits as nums

from bdec import DecodeError
from bdec.choice import Choice
from bdec.constraints import Equals
from bdec.data import Data
from bdec.entry import is_hidden
from bdec.expression import LengthResult
from bdec.field import Field
from bdec.sequence import Sequence
from bdec.sequenceof import SequenceOf

alphanums = alphas + nums

class ParseException(DecodeError):
    def __init__(self, ex):
        DecodeError.__init__(self, ex.entry)
        self.error = ex

    def __str__(self):
        return str(self.error)


class ParserElement:
    def __init__(self):
        self._actions = []
        self._internal_actions = []

    def _createEntry(self, separator):
        raise NotImplementedError()

    def createDecoder(self, separator):
        result = self._createEntry(separator)
        result.actions = self._internal_actions + self._actions
        return result

    def setParseAction(self, fn):
        self._actions = [fn]

    def parseString(self, text):
        try:
            return self._decode(text)
        except DecodeError, ex:
            raise ParseException(ex)

    def _decode(self, text):
        whitespace = ZeroOrMore(Literal(' '))
        whitespace.setParseAction(lambda t:[])

        # Whitespace is decoded at the end of the Literal (and Word) entries,
        # so we have to decode any leading whitespace. The alternative,
        # decoding the whitespace before Literal (and Word) entries, would
        # prevent the Chooser from being able to guess the type.
        decoder = Sequence(None, [whitespace.createDecoder(None), self.createDecoder(whitespace)])

        stack = []
        tokens = []
        data = Data(text)
        for is_starting, name, entry, data, value in decoder.decode(data):
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

                # Extend the current tokens list with the child tokens
                stack[-1].extend(tokens)
                tokens = stack.pop()
        assert len(stack) == 0
        return tokens

    def __add__(self, other):
        return And([self, other])

    def __ladd__(self, other):
        return And([other, self])


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
        self.text = text

    def _createEntry(self, separator):
        result = Field('literal', length=len(self.text) * 8, format=Field.TEXT, constraints=[Equals(self.text)])
        if separator:
            result = Sequence('literal', [result, separator.createDecoder(None)])
        return result

    def __str__(self):
        return '"%s"' % self.text


class Word(ParserElement):
    def __init__(self, chars):
        ParserElement.__init__(self)
        self.chars = chars

    def _element(self):
        return OneOrMore(Or([Literal(c) for c in self.chars]))

    def _createEntry(self, separator):
        entry = self._element().createDecoder(None)
        self._internal_actions.append(lambda t: [''.join(t)])
        if separator:
            entry = Sequence('word', [entry, separator.createDecoder(None)])
        return entry

    def __str__(self):
        return str(self._element())


class And(ParserElement):
    def __init__(self, exprs):
        ParserElement.__init__(self)
        self.exprs = exprs

    def _createEntry(self, separator):
        return Sequence('and', [e.createDecoder(separator) for e in self.exprs])

    def __add__(self, other):
        return And(self.exprs + [other])

    def __str__(self):
        return ', '.join(str(e) for e in self.exprs)


class Or(ParserElement):
    def __init__(self, exprs):
        ParserElement.__init__(self)
        self.exprs = exprs

    def _createEntry(self, separator):
        return Choice('or', [e.createDecoder(separator) for e in self.exprs])

    def __str__(self):
        return '[%s]' % (', '.join(str(e) for e in self.exprs))

class StringEnd(ParserElement):
    def _createEntry(self, separator):
        data = Choice('data:', [Field(None, length=8), Sequence(None, [])])
        length_check = Sequence(None, [], value=LengthResult('data:'), constraints=[Equals(0)])
        return Sequence(None, [data, length_check])
