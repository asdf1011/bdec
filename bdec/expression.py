#   Copyright (C) 2010 Henry Ludemann
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
#  
# This file incorporates work covered by the following copyright and  
# permission notice:  
#  
#   Copyright (c) 2010, PRESENSE Technologies GmbH
#   All rights reserved.
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#       * Redistributions of source code must retain the above copyright
#         notice, this list of conditions and the following disclaimer.
#       * Redistributions in binary form must reproduce the above copyright
#         notice, this list of conditions and the following disclaimer in the
#         documentation and/or other materials provided with the distribution.
#       * Neither the name of the PRESENSE Technologies GmbH nor the
#         names of its contributors may be used to endorse or promote products
#         derived from this software without specific prior written permission.
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#   ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#   WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#   DISCLAIMED. IN NO EVENT SHALL PRESENSE Technologies GmbH BE LIABLE FOR ANY
#   DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import bdec.data as dt
import operator

# A list of supported operators, in order of precedence
_operators = [
        [
            ('*', operator.mul),
            ('/', operator.div),
            ('%', operator.mod),
        ],
        [
            ('+', operator.add),
            ('-', operator.sub),
        ],
        [
            ('<<', operator.lshift),
            ('>>', operator.rshift),
        ],
    ]


class UndecodedReferenceError(Exception):
    """
    Raised when a decoded entry is referenced (but unused).

    We don't derive this from DecodeError, as it is an internal program error.
    """
    def __init__(self, name, context):
        self.name = name
        self.context = context

    def __str__(self):
        return "Missing context '%s' (have %s)" % (self.name,
                ', '.join("'%s'" % k for k in self.context.keys()))

class NullReferenceError(UndecodedReferenceError):
    def __str__(self):
        return "Context '%s' present, but is None!" % self.name

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

    def __mul__(self, other):
        return ArithmeticExpression(operator.mul, self, other)

    def __div__(self, other):
        return ArithmeticExpression(operator.div, self, other)

    def __mod__(self, other):
        return ArithmeticExpression(operator.mod, self, other)

    def __add__(self, other):
        return ArithmeticExpression(operator.add, self, other)

    def __sub__(self, other):
        return ArithmeticExpression(operator.sub, self, other)

    def __lshift__(self, other):
        return ArithmeticExpression(operator.lshift, self, other)

    def __rshift__(self, other):
        return ArithmeticExpression(operator.rshift, self, other)


class ArithmeticExpression(Expression):
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

    def __repr__(self):
        lookup = {}
        for ops in _operators:
            lookup.update((op, name) for name, op in ops)
        return '(%s %s %s)' % (self.left, lookup[self.op], self.right)


class RoundUpDivisionExpression(Expression):
    """Class to implement division with an optional rounding up.

    The division is round to minus infinity.
    """
    def __init__(self, numerator, denominator, should_round_up):
        self.numerator = numerator
        self.denominator = denominator
        self.should_round_up = should_round_up

    def evaluate(self, context):
        numerator = self.numerator.evaluate(context)
        denominator = self.denominator.evaluate(context)

        # In python -ve / +ve will round towards minus infinity, so we only
        # need to handle the round up case.
        result = numerator / denominator
        if numerator % denominator and self.should_round_up:
            result += 1
        return result


class Constant(Expression):
    def __init__(self, value):
        self.value = value
        
    def evaluate(self, context):
        return self.value

    def __repr__(self):
        if isinstance(self.value, dt.Data):
            value = self.value
            if len(value) % 8:
                # We can only convert bytes to hex, so added a '0' data
                # object in front.
                leading_bits = 8 - len(value) % 8
                value = dt.Data('\x00', start=0, end=leading_bits) + value
            return '0x%s' % value.get_hex()
        elif isinstance(self.value, int) and self.value % 8 == 0 and \
                self.value / 8 > 1:
            # It can be clearer to return numbers in bytes
            return "%i * 8" % (self.value / 8)
        return str(self.value)


class ReferenceExpression(Expression):
    """A reference to a value or length of another entry."""
    def __init__(self, name):
        assert isinstance(name, basestring)
        self.name = name

    def param_name(self):
        raise NotImplementedError()

    def evaluate(self, context):
        try:
            result = context[self.param_name()]
        except KeyError:
            raise UndecodedReferenceError(self.param_name(), context)
        if result is None:
            raise NullReferenceError(self.param_name(), context)
        return result

    def __eq__(self, other):
        if type(self) != type(other):
            return NotImplemented
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


class ValueResult(ReferenceExpression):
    """
    Object returning the result of a entry when cast to an integer.
    """
    def param_name(self):
        return self.name

    def __repr__(self):
        return '${%s}' % self.name


class LengthResult(ReferenceExpression):
    """
    Object returning the length of a decoded entry.
    """
    def param_name(self):
        return self.name + ' length'

    def __repr__(self):
        return "len{%s}" % self.name


def _half(op):
    """
    Create a handler to handle half of a binary expression.

    The handler returns a callable object that takes the second half
    of the binary expression.
    """
    def handler(s,l,t):
        return lambda left: ArithmeticExpression(op, left, t[1])
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

def _int_expression():
    from pyparsing import Word, alphanums, nums, Forward, ZeroOrMore, Combine, CaselessLiteral, srange, ParserElement
    entry_name = Word(alphanums + ' _+:.-')
    integer = Word(nums).addParseAction(lambda s,l,t: [Constant(int(t[0]))])
    hex = Combine(CaselessLiteral("0x") + Word(srange("[0-9a-fA-F]"))).addParseAction(lambda s,l,t:[Constant(int(t[0][2:], 16))])
    named_reference = ('${' + entry_name + '}').addParseAction(lambda s,l,t:ValueResult(t[1]))
    length_reference = ('len{' + entry_name + '}').addParseAction(lambda s,l,t:LengthResult(t[1]))

    expression = Forward()
    factor = hex | integer | named_reference | length_reference | ('(' + expression + ')').addParseAction(lambda s,l,t:t[1])

    entry = factor
    for ops in _operators:
        op_parse = reduce(operator.or_,
                [(character + entry).addParseAction(_half(op)) for character, op in ops])
        entry = (entry + ZeroOrMore(op_parse)).addParseAction(_collapse)
    expression << entry
    return expression

def parse(text):
    """
    Compile a length expression into an integer convertible object.

    :param name_lookup: A object to call to query a named integer 
        convertible object.
    return -- An Expression instance
    """
    from pyparsing import StringEnd, ParseException
    complete = _int_expression() + StringEnd()
    try:
        return complete.parseString(text)[0]
    except ParseException, ex:
        raise ExpressionError(ex)
# Legacy name for parse function
compile = parse

def parse_conditional_inverse(text):
    """
    Parse a boolean expression.

    text -- A text string to be parsed.
    return -- A bdec.entry.Entry instance that will decode if the conditional
        is _false_ (eg: the returned entry can be used as a 'not present' 
        option in a choice).
    """
    from pyparsing import StringEnd, ParseException
    from pyparsing import Forward, OneOrMore, Literal, ZeroOrMore
    from bdec.constraints import Equals, Minimum, Maximum, NotEquals
    import bdec.choice as chc
    import bdec.sequence as seq

    bool_int_operators = [
            ('>', Maximum),
            ('>=', lambda limit: Maximum(ArithmeticExpression(operator.sub, limit, Constant(1)))),
            ('<', Minimum),
            ('<=', lambda limit: Minimum(ArithmeticExpression(operator.add, limit, Constant(1)))),
            ('==', NotEquals),
            ('!=', Equals),
            ]


    # Create an expression for parsing the 'comparators'; eg 'a > b'
    integer = _int_expression()
    def create_action(handler):
        return lambda s,l,t:seq.Sequence('condition:', [], value=t[0], constraints=[handler(t[2])])
    int_expressions = []
    for name, handler in bool_int_operators:
        int_expressions.append((integer + name + integer).addParseAction(create_action(handler)))

    implicit_int_to_bool = integer.copy().addParseAction(
            lambda s,l,t:seq.Sequence('condition', [], value=t[0], constraints=[Equals(0)]))
    int_bool_expr = reduce(operator.or_, int_expressions) | implicit_int_to_bool

    # Create an expression for parsing the boolean operations; eg: 'a && b'
    bool_expr = Forward()
    factor = int_bool_expr | ('(' + bool_expr + ')').addParseAction(lambda s,l,t:t[1])

    or_ = Literal('||') | 'or'
    or_expression = OneOrMore(or_ + factor).addParseAction(lambda s,l,t:(seq.Sequence, t[1::2]))

    and_ = Literal('&&') | 'and'
    and_expression = OneOrMore(and_ + factor).addParseAction(lambda s,l,t:(chc.Choice, t[1::2]))

    # Join all 'and' and 'or' conditions
    def _collapse_bool(s,l,t):
        result = t.pop(0)
        while t:
            cls, children = t.pop(0)
            children.insert(0, result)
            result = cls('condition', children)
        return result
    bool_expr << (factor + ZeroOrMore(and_expression | or_expression)).addParseAction(_collapse_bool)

    # Parse the string
    complete = bool_expr + StringEnd()
    try:
        return complete.parseString(text)[0]
    except ParseException, ex:
        raise ExpressionError(ex)

