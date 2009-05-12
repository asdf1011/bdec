#   Copyright (C) 2008 Henry Ludemann
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

import operator

_operators1 = [
        ('*', operator.mul),
        ('/', operator.div),
        ('%', operator.mod),
        ]

_operators2 = [
        ('+', operator.add),
        ('-', operator.sub),
        ]

class UndecodedReferenceError(Exception):
    """
    Raised when a decoded entry is referenced (but unused).

    We don't derive this from DecodeError, as it is an internal program error.
    """

class ExpressionError(Exception):
    def __init__(self, ex):
        self.error = ex

    def __str__(self):
        return str(self.error)

class Expression(object):
    """
    An object that returns a value given the current decode context.
    """
    def evaluate(self, context):
        raise NotImplementedError


class Delayed(Expression):
    """
    Class to delay the operation of an integer operation.

    This is because some parts of an expression may not be accessible until
    the expression is used (for example, an expression object that
    references the decoded value of another field).
    """
    def __init__(self, op, left, right):
        self.op = op
        assert isinstance(left, Expression)
        assert isinstance(right, Expression)
        self.left = left
        self.right = right

    def evaluate(self, context):
        return self.op(self.left.evaluate(context), self.right.evaluate(context))

    def __str__(self):
        lookup = {}
        lookup.update((op, name) for name, op in _operators1)
        lookup.update((op, name) for name, op in _operators2)
        return '(%s %s %s)' % (self.left, lookup[self.op], self.right)


class Constant(Expression):
    def __init__(self, value):
        self.value = value
        
    def evaluate(self, context):
        return self.value

    def __str__(self):
        if isinstance(self.value, int) and self.value % 8 == 0 and \
                self.value / 8 > 1:
            # It can be clearer to return numbers in bytes
            return "%i * 8" % (self.value / 8)
        return str(self.value)


class ValueResult(Expression):
    """
    Object returning the result of a entry when cast to an integer.
    """
    def __init__(self, name):
        assert isinstance(name, basestring)
        self.name = name

    def evaluate(self, context):
        try:
            return context[self.name]
        except KeyError:
            raise UndecodedReferenceError()

    def __str__(self):
        return '${%s}' % self.name


class LengthResult(Expression):
    """
    Object returning the length of a decoded entry.
    """
    def __init__(self, name):
        assert isinstance(name, basestring)
        self.name = name

    def evaluate(self, context):
        try:
            return context[self.name + ' length']
        except KeyError:
            raise UndecodedReferenceError()

    def __str__(self):
        return "len{%s}" % self.name


def _half(op):
    """
    Create a handler to handle half of a binary expression.

    The handler returns a callable object that takes the second half
    of the binary expression.
    """
    def handler(s,l,t):
        return lambda left: Delayed(op, left, t[1])
    return handler

def _collapse(s,l,t):
    """
    Collapse a series of half binary expressions into one.
    """
    # Note that here we are assuming the first item is complete, and
    # the rest of the items are 'half' expressions.
    result = t[0]
    for next in t[1:]:
        result = next(result)
    return result

def compile(text):
    """
    Compile a length expression into an integer convertible object.

    :param name_lookup: A object to call to query a named integer 
        convertible object.
    return -- An Expression instance
    """
    from pyparsing import Word, alphanums, nums, Forward, StringEnd, ZeroOrMore, ParseException, Combine, CaselessLiteral, srange
    entry_name = Word(alphanums + ' _+:.-')
    integer = Word(nums).addParseAction(lambda s,l,t: [Constant(int(t[0]))])
    hex = Combine(CaselessLiteral("0x") + Word(srange("[0-9a-fA-F]"))).addParseAction(lambda s,l,t:[Constant(int(t[0][2:], 16))])
    named_reference = ('${' + entry_name + '}').addParseAction(lambda s,l,t:ValueResult(t[1]))
    length_reference = ('len{' + entry_name + '}').addParseAction(lambda s,l,t:LengthResult(t[1]))

    expression = Forward()
    factor = hex | integer | named_reference | length_reference | ('(' + expression + ')').addParseAction(lambda s,l,t:t[1])

    ops1 = reduce(operator.or_,
            [(character + factor).addParseAction(_half(op)) for character, op in _operators1])
    term = (factor + ZeroOrMore(ops1)).addParseAction(_collapse)

    ops2 = reduce(operator.or_,
            [(character + term).addParseAction(_half(op)) for character, op in _operators2])
    expression << (term + ZeroOrMore(ops2)).addParseAction(_collapse)

    complete = expression + StringEnd()
    try:
        return complete.parseString(text)[0]
    except ParseException, ex:
        raise ExpressionError(ex)
