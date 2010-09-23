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

from bdec import DecodeError
from bdec.expression import ArithmeticExpression, Constant, \
    ReferenceExpression, ValueResult
from bdec.inspect.type import expression_range as erange

class SolverError(DecodeError):
    def __init__(self, entry, expr, reason):
        DecodeError.__init__(self, entry)
        self.expr = expr
        self.reason = reason

    def __str__(self):
        return "%s: %s" % (self.reason, self.expr)

class UnsolvableExpressionError(SolverError):
    def __init__(self, entry, expression, expected):
        SolverError.__init__(self, entry, expression, None)
        self.expected = expected

    def __str__(self):
        return 'Unsolvable exression: %s != %s' % (self.expr, self.expected)


def _break_into_parts(entry, expression, input_params):
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
        left, lconst = _break_into_parts(entry, expression.left, input_params)
        right, rconst = _break_into_parts(entry, expression.right, input_params)
        if expression.op in (operator.add, operator.sub):
            # We need to add / subtract the common components
            constant = ArithmeticExpression(expression.op, lconst, rconst)
            result = left
            for ref, expr in right.items():
                existing = result.get(ref, Constant(0))
                result[ref] = ArithmeticExpression(expression.op, existing, expr)
        elif left and right:
            # We can't able to handle the case where the left & right _both_
            # have parameters for non addition / subtraction. Or at least, we
            # don't attempt to at the moment...
            raise SolverError(entry, expression, 'Unable to handle expression where left and right are non constant')
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
                    raise SolverError(entry, expression, 'Shifting by a non constant not supported')
                for ref, expr in left.items():
                    result[ref] = expr << rconst
                constant = lconst << rconst
            else:
                raise SolverError(entry, expression, 'Breaking apart expressions with %s not supported' % expression.op)
    elif isinstance(expression, Constant):
        constant = expression
    elif isinstance(expression, ReferenceExpression):
        if expression.param_name() not in input_params:
            # This is one of the parameters that we need to solve
            result[expression] = expression
        else:
            # We know the value of this parameter; treat it as constant.
            constant = expression
    else:
        raise Exception("Unknown expression entry %s!" % expression)
    return result, constant

def _is_constant(entry, expression, input_params):
    references, constant = _break_into_parts(entry, expression, input_params)
    return not references

def _invert(result_expr, entry, expression, input_params):
    """Convert a function value=f(x) into x=f(value)"""
    left = result_expr
    right = expression

    # Reduce 'right' until it is just the single parameter
    while not isinstance(right, ReferenceExpression):
        if isinstance(right, ArithmeticExpression):
            is_left_const = _is_constant(entry, right.left, input_params)
            is_right_const = _is_constant(entry, right.right, input_params)
            if not is_left_const and not is_right_const:
                # The code doesn't handle the same entry being referenced
                # multiple times at the moment... (eg: y = x + x)
                raise SolverError(entry, expression, 'Unable to invert '
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
            elif is_left_const and right.op == operator.sub:
                # left = k - right  ->   k - left = right
                left = ArithmeticExpression(operator.sub, right.left, left)
                right = right.right
            elif is_left_const and right.op == operator.add:
                # left = k + right  ->   left - k = right
                left = ArithmeticExpression(operator.sub, left, right.left)
                right = right.right
            else:
                raise SolverError(entry, expression, 'Unable to invert '
                        'expressions containing operator %s' % right.op)
        else:
            raise SolverError(entry, expression, 'Right expression is not '
                    'an arithmetic expression')
    return left

def solve_expression(result_expr, expression, entry, params, input_params):
    """Get a list of expression for solving the given expression.
    
    return -- A (constant, [(reference, expression, inverted)]), where constant is
        a constant expression, and the reference / expression / inverted  tuple is
        the reference to an unknown parameter, the portion of the expression that
        is made up of this entry, and the inverted expression to calculate
        its value given it's component of the expression. """
    components, constant = _break_into_parts(entry, expression, input_params)
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
    return constant, [(ref, expr, _invert(result_expr, entry, expr, input_params)) for ref, expr in variables]

def solve(expression, entry, params, context, value):
    """Solve an expression given the result and the input parameters.

    expression -- A bdec.expression.Expression instance to solve.
    params -- A bdec.param.ExpressionParameters instance used to query all
        values passed into the expression.
    value -- The integer value to use when solving the expression.
    context -- A dict of (name:value) representing all known parameter
        values that can be used for solving.
    result -- Returns a dict of {ReferenceExpression: value} """

    # Figure out the components by working out each item independantly,
    # starting with the most significant. We create a reference to a
    # 'solve result' variable which we will reference in the inverted
    # expressions.
    solve_result = ValueResult('solve result')
    constant, variables = solve_expression(solve_result, expression, entry, params, context.keys())
    result = {}
    original_value = value
    value -= constant.evaluate(context)
    for ref, expr, inverted_expr in variables:
        # Work out a value for this variable
        c = context.copy()
        c[solve_result.name] = value
        result[ref] = inverted_expr.evaluate(c)

        # Remove it's impact from the overall value so we can work out the next
        # variable
        c = context.copy()
        c[ref.param_name()] = result[ref]
        value -= expr.evaluate(c)
    if value != 0:
        raise UnsolvableExpressionError(entry, expression, original_value)
    return result

