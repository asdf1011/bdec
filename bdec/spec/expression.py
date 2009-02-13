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

import bdec.spec
import operator

class UndecodedReferenceError(Exception):
    """
    Raised when a decoded entry is referenced (but unused).

    We don't derive this from DecodeError, as it is an internal program error.
    """

class ExpressionError(bdec.spec.LoadError):
    def __init__(self, ex):
        self.error = ex

    def __str__(self):
        return str(self.error)

class Expression(object):
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
        return '(%s %s %s)' % (self.left, self.op, self.right)


class Constant(Expression):
    def __init__(self, value):
        self.value = value
        
    def evaluate(self, context):
        return self.value

    def __str__(self):
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
        return self.name


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
        return "%s length" % self.name


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

    mul = ('*' + factor).addParseAction(_half(operator.mul))
    div = ('/' + factor).addParseAction(_half(operator.div))
    mod = ('%' + factor).addParseAction(_half(operator.mod))
    term = (factor + ZeroOrMore(mul | div | mod)).addParseAction(_collapse)

    add = ('+' + term).addParseAction(_half(operator.add))
    sub = ('-' + term).addParseAction(_half(operator.sub))
    expression << (term + ZeroOrMore(add | sub)).addParseAction(_collapse)

    complete = expression + StringEnd()
    try:
        return complete.parseString(text)[0]
    except ParseException, ex:
        raise ExpressionError(ex)
