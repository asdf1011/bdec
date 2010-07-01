# Copyright (c) 2010, PRESENSE Technologies GmbH
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the PRESENSE Technologies GmbH nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import operator

from bdec.expression import ArithmeticExpression, Constant, \
    ReferenceExpression, ValueResult
from bdec.inspect.type import expression_range as erange

class SolverError(Exception):
    def __init__(self, expr, reason):
        self.expr = expr
        self.reason = reason

    def __str__(self):
        return "%s: %s" % (self.reason, self.expr)

class UnsolvableExpressionError(SolverError):
    def __init__(self, expression, expected):
        SolverError.__init__(self, expression, None)
        self.expected = expected

    def __str__(self):
        return 'Unsolvable exression: %s != %s' % (self.expr, self.expected)


def _break_into_parts(expression):
    """Break an expression into individual expressions.

    Each individual expression should have a single parameter referenced,
    although it may be referenced multiple times.
    
    return -- A tuple containing
        ({bdec.expression.ReferenceExpression: expression}, constant_expr).
        The input expression will be equal to the sum of the result
        components."""
    result = {}
    constant = Constant(0)
    if isinstance(expression, ArithmeticExpression):
        left, lconst = _break_into_parts(expression.left)
        right, rconst = _break_into_parts(expression.right)
        if expression.op in (operator.add, operator.sub):
            # We need to add / subtract the common components
            constant = ArithmeticExpression(expression.op, lconst, rconst)
            result = left
            for ref, expr in right.items():
                if ref in result:
                    result[ref] = ArithmeticExpression(expression.op, result[ref], expr)
                else:
                    result[ref] = expr
        elif left and right:
            # We can't able to handle the case where the left & right _both_
            # have parameters for non addition / subtraction. Or at least, we
            # don't attempt to at the moment...
            raise SolverError(expression, 'Unable to handle expression where left and right are non constant')
        else:
            # Either the left or right expression has a non constant value of 0.
            if expression.op == operator.mul:
                #   f(y) = (left(params) + kl) * (right(params) + kr)
                # where left(params) or right(params) is zero. So the result will be
                #   f(y) = kr * left(params) + kl * right(params) + kl * kr
                for ref, expr in left.items():
                    result[ref] = expr * rconst
                for ref, expr in right.items():
                    result[ref] = expr * lconst
                constant = lconst * rconst
            elif expression.op == operator.lshift:
                if right:
                    # Don't support shifting by a non-constant
                    raise SolverError(expression, 'Shifting by a non constant not supported')
                for ref, expr in left.items():
                    result[ref] = expr << rconst
                constant = constant << rconst
            else:
                raise SolverError(expression, 'Breaking apart expressions with %s not supported' % expression.op)
    elif isinstance(expression, Constant):
        constant = expression
    elif isinstance(expression, ReferenceExpression):
        result[expression] = expression
    else:
        raise Exception("Unknown expression entry %s!" % expression)
    return result, constant

def _is_constant(expression):
    references, constant = _break_into_parts(expression)
    return not references

def _invert(expression):
    """Convert a function value=f(x) into x=f(value)"""
    left = ValueResult('result')
    right = expression

    # Reduce 'right' until it is just the single parameter
    while not isinstance(right, ReferenceExpression):
        if isinstance(right, ArithmeticExpression):
            is_left_const = _is_constant(right.left)
            is_right_const = _is_constant(right.right)
            if not is_left_const and not is_right_const:
                # The code doesn't handle the same entry being referenced
                # multiple times at the moment... (eg: y = x + x)
                raise SolverError(expression, 'Unable to invert '
                        'expressions where the same entry is referenced on '
                        'the left and right of an expression')
            if right.op == operator.mul:
                if is_right_const:
                    # left = right * k  ->   left / k = right
                    left = ArithmeticExpression(operator.div, left, right.right)
                    right = right.left
                else:
                    # left = k * right  -> left / k = right
                    left = ArithmeticExpression(operator.div, left, right.left)
                    right = right.right
            elif is_right_const and right.op == operator.lshift:
                left = ArithmeticExpression(operator.rshift, left, right.right)
                right = right.left
            else:
                raise SolverError(expression, 'Unable to invert '
                        'expressions containing operator %s' % right.op)
        else:
            raise SolverError(expression, 'Right expression is not '
                    'an arithmetic expression')
    return left

def solve(expression, entry, params, value):
    """Solve an expression given the result and the input parameters.
    
    expression -- A bdec.expression.Expression instance to solve.
    params -- A list of bdec.param.Param instances representing all values
        passed into the expression.
    value -- The integer value to use when solving the expression.
    result -- Returns a dict of {ReferenceExpression: value} """
    components, constant = _break_into_parts(expression)

    # Sort the components in order influence on the output
    def influence(component):
        reference, expression = component
        output = erange(expression, entry, params)
        result = 0
        if output.min:
            result = max(abs(output.min), result)
        if output.max:
            result = max(abs(output.max), result)
        return result
    variables = sorted(components.items(), key=influence, reverse=True)

    # Figure out the components by working out each item independantly,
    # starting with the most significant.
    result = {}
    original_value = value
    value -= constant.evaluate({})
    for ref, expr in variables:
        result[ref] = _invert(expr).evaluate({'result' : value})
        value -= expr.evaluate({ref.name:result[ref]})
    if value != 0:
        raise UnsolvableExpressionError(expression, original_value)
    return result

