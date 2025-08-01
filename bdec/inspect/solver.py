#   Copyright (C) 2011-2012 Henry Ludemann
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

import operator
import z3

from bdec import DecodeError
from bdec.expression import ArithmeticExpression, Constant, \
    ReferenceExpression, ValueResult, RoundUpDivisionExpression
from bdec.inspect.range import Range
from bdec.inspect.type import expression_range as erange

class SolverError(Exception):
    """ This isn't an encoding error, but rather a specification, or internal error.

    Treating it as an encoding error could cause encoding to continue, but
    with a different option in a choice (which is wrong)."""
    def __init__(self, entry, expr, reason):
        self.entry = entry
        self.expr = expr
        self.reason = reason

    def __str__(self):
        return "%s: %s" % (self.reason, self.expr)

class UnsolvableExpressionError(SolverError):
    def __init__(self, entry, expression, expected):
        SolverError.__init__(self, entry, expression, None)
        self.expected = expected

    def __str__(self):
        return 'Unsolvable expression: %s == %s' % (self.expr, self.expected)


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
            elif expression.op == operator.truediv:
                if right:
                    raise SolverError(entry, expression, 'Dividing by a non-constant not supported')
                if len(left) > 1:
                    raise SolverError(entr, expression, 'Dividing two unknowns not supported.')
                for ref, expr in left.items():
                    result[ref] = expr / rconst
                constant = lconst / rconst
            elif expression.op == operator.mod:
                if right:
                    raise SolverError(entry, expression, 'Modding by a non-constant not supported')
                for ref, expr in left.items():
                    result[ref] = expr % rconst
                constant = lconst % rconst
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

def _invert(result_expr, entry, expression, params, input_params, remainder_range):
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
                    left = ArithmeticExpression(operator.truediv, left, right.right)
                    right = right.left
                else:
                    # left = k * right  -> left / k = right
                    left = ArithmeticExpression(operator.truediv, left, right.left)
                    right = right.right

                # To correctly handle solving signed integers, eg:
                #    y = (-signed * k) + value
                # we have to ensure that '-signed / k' is always less than 'y',
                # as 'value >= 0'. Thus we need to ensure that the inverted
                # '/' always rounds towards negative infinity. To ensure this
                # we check to see if we erased any bits in the divide; if so, we
                # need to account for the rounding.
                #
                # To know if we need to round down or up, we need to see
                # whether we will be positive or negative, and likewise the
                # value of the remainder. For example, if our output will be
                # negative (eg: remainder = -signed * k), and the remainder
                # will be positive (eg: y = value) then we must round UP (so
                # that the remainder will be positive when solving 'value').
                # Conversely, if both this expression and the remainder have
                # the same sign, there is no need for rounding...
                our_range = erange(expression, entry, params)
                should_round_up = False
                if (our_range.min is None or our_range.min < 0) and \
                        (remainder_range.max is None or remainder_range.max > 0):
                    # We are negative, remainder is positive; we need to round up.
                    should_round_up = True
                elif (our_range.max is None or our_range.max > 0) and \
                        (remainder_range.min is None or remainder_range.min < 0):
                    # We are positive, remainder is negative; we need to round up.
                    should_round_up = True
                left = RoundUpDivisionExpression(left.left, left.right, should_round_up)
            elif is_right_const and right.op == operator.lshift:
                # left = right << k  ->  left >> k = right
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
    """Get a list of expressions for solving the given expression. For example,
    for
       y = 2 * x + 5
    'y' is the result expression, '2 * x + 5' is the expression, it would
    solve to a constant of 5, and x = y / 2.

    result_expr -- An expression for the result.
    expression -- The expression we want to solve.
    entry -- The entry where this expression is used. This is used to resolve
        references to entries.
    params -- A bdec.inspect.param.ExpressionParameters instance, used to
        determine ranges of references.
    input_params -- A list of parameters that are 'known'. Any references to
        these parameters will be treated as constant.
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
        if output.min is not None and output.max is not None:
            result = max(abs(output.min), result)
            result = max(abs(output.max), result)
        else:
            # As we have either no minimum or maximum, our influence will
            # be really big.
            result = 1e1024
        return result
    variables = sorted(components.items(), key=influence, reverse=True)
    result_params = []
    for i, (ref, expr) in enumerate(variables):
        # Get the range of the remaining references (required so we know what
        # way we should be rounding divisions / shifts).
        remaining_range = sum((erange(c[1], entry, params) for c in variables[i+1:]),
                Range(0, 0))
        result_params.append((ref, expr, _invert(result_expr, entry, expr,
            params, input_params, remaining_range)))
    return constant, result_params

def _expression_to_z3(expression, vars_map, context):
    """Convert a bdec Expression to a Z3 expression.
    
    expression -- A bdec.expression.Expression instance
    vars_map -- Dict mapping parameter names to Z3 variables
    context -- Dict of known parameter values
    return -- Z3 expression
    """
    if isinstance(expression, Constant):
        return z3.IntVal(expression.value)
    elif isinstance(expression, ReferenceExpression):
        param_name = expression.param_name()
        if param_name in context:
            # Known value, treat as constant
            return z3.IntVal(context[param_name])
        else:
            # Unknown value, create Z3 variable if not exists
            if param_name not in vars_map:
                vars_map[param_name] = z3.Int(param_name)
            return vars_map[param_name]
    elif isinstance(expression, ArithmeticExpression):
        left_z3 = _expression_to_z3(expression.left, vars_map, context)
        right_z3 = _expression_to_z3(expression.right, vars_map, context)
        
        if expression.op == operator.add:
            return left_z3 + right_z3
        elif expression.op == operator.sub:
            return left_z3 - right_z3
        elif expression.op == operator.mul:
            return left_z3 * right_z3
        elif expression.op == operator.truediv:
            return left_z3 / right_z3
        elif expression.op == operator.mod:
            return left_z3 % right_z3
        elif expression.op == operator.lshift:
            return left_z3 * (2 ** right_z3)
        elif expression.op == operator.rshift:
            return left_z3 / (2 ** right_z3)
        else:
            raise SolverError(None, expression, f'Unsupported operator: {expression.op}')
    elif isinstance(expression, RoundUpDivisionExpression):
        # Handle round up division - convert to Z3 equivalent
        numerator_z3 = _expression_to_z3(expression.numerator, vars_map, context)
        denominator_z3 = _expression_to_z3(expression.denominator, vars_map, context)
        if expression.should_round_up:
            # Ceiling division: (a + b - 1) / b
            return (numerator_z3 + denominator_z3 - 1) / denominator_z3
        else:
            return numerator_z3 / denominator_z3
    else:
        raise SolverError(None, expression, f'Unsupported expression type: {type(expression)}')

def _get_reference_expressions(expression):
    """Extract all ReferenceExpression instances from an expression tree."""
    refs = []
    if isinstance(expression, ReferenceExpression):
        refs.append(expression)
    elif isinstance(expression, ArithmeticExpression):
        refs.extend(_get_reference_expressions(expression.left))
        refs.extend(_get_reference_expressions(expression.right))
    elif isinstance(expression, RoundUpDivisionExpression):
        refs.extend(_get_reference_expressions(expression.numerator))
        refs.extend(_get_reference_expressions(expression.denominator))
    return refs

def _extract_field_constraints(entry, params):
    """Extract field constraints from entry hierarchy and map them to expression variables.
    
    Returns a dict mapping parameter names to (min_val, max_val) tuples.
    """
    from bdec.constraints import Minimum, Maximum
    from bdec.field import Field
    from bdec.sequence import Sequence
    from bdec.entry import Child
    import operator
    
    constraints = {}
    visited = set()  # Prevent infinite recursion
    
    def _visit_entry(ent, entry_name=None):
        # Prevent infinite recursion by tracking visited (entry, name) pairs
        entry_key = (id(ent), entry_name)
        if entry_key in visited:
            return
        visited.add(entry_key)
        # If this entry has a value expression, we need to propagate constraints
        if hasattr(ent, 'value') and ent.value is not None and entry_name:
            # This entry's value might be referenced by the expression
            # We need to trace constraints from child fields to this entry's value
            field_constraints = {}
            
            # Collect constraints from child fields
            if hasattr(ent, 'children'):
                for child in ent.children:
                    child_entry = child.entry if hasattr(child, 'entry') else child
                    if isinstance(child_entry, Field) and child_entry.constraints:
                        child_min = None
                        child_max = None
                        
                        for constraint in child_entry.constraints:
                            try:
                                limit = constraint.limit.evaluate({})
                                if isinstance(constraint, Minimum):
                                    child_min = limit
                                elif isinstance(constraint, Maximum):
                                    child_max = limit
                            except:
                                pass
                        
                        if child_min is not None or child_max is not None:
                            field_constraints[child_entry.name] = (child_min, child_max)
            
            # If we have field constraints and this entry has a value expression,
            # try to propagate the constraints to the entry's value
            if field_constraints and hasattr(ent, 'value'):
                propagated_constraints = _propagate_constraints_through_expression(
                    ent.value, field_constraints)
                if propagated_constraints:
                    constraints[entry_name] = propagated_constraints
        
        # Also check if this entry itself is a field with constraints
        if isinstance(ent, Field) and ent.constraints:
            min_val = None
            max_val = None
            
            for constraint in ent.constraints:
                try:
                    limit = constraint.limit.evaluate({})
                    if isinstance(constraint, Minimum):
                        min_val = limit
                    elif isinstance(constraint, Maximum):
                        max_val = limit
                except:
                    pass
            
            if min_val is not None or max_val is not None:
                name = entry_name or ent.name
                constraints[name] = (min_val, max_val)
        
        # Recursively visit children
        if hasattr(ent, 'children'):
            for child in ent.children:
                child_entry = child.entry if hasattr(child, 'entry') else child
                child_name = child.name if hasattr(child, 'name') else None
                _visit_entry(child_entry, child_name)
    
    _visit_entry(entry)
    return constraints

def _propagate_constraints_through_expression(value_expr, field_constraints):
    """Propagate field constraints through a value expression.
    
    For example, if field 'char:' has constraints [48, 57] and the value expression
    is '${char:} - 48', then the resulting value should have constraints [0, 9].
    """
    # Handle simple cases: ${field} + constant, ${field} - constant
    if isinstance(value_expr, ArithmeticExpression):
        if isinstance(value_expr.left, ReferenceExpression) and isinstance(value_expr.right, Constant):
            field_name = value_expr.left.param_name()
            if field_name in field_constraints:
                field_min, field_max = field_constraints[field_name]
                constant_val = value_expr.right.value
                
                if value_expr.op == operator.add:
                    # value = field + constant
                    result_min = field_min + constant_val if field_min is not None else None
                    result_max = field_max + constant_val if field_max is not None else None
                    return (result_min, result_max)
                elif value_expr.op == operator.sub:
                    # value = field - constant  
                    result_min = field_min - constant_val if field_min is not None else None
                    result_max = field_max - constant_val if field_max is not None else None
                    return (result_min, result_max)
        elif isinstance(value_expr.right, ReferenceExpression) and isinstance(value_expr.left, Constant):
            field_name = value_expr.right.param_name()
            if field_name in field_constraints:
                field_min, field_max = field_constraints[field_name]
                constant_val = value_expr.left.value
                
                if value_expr.op == operator.add:
                    # value = constant + field
                    result_min = constant_val + field_min if field_min is not None else None
                    result_max = constant_val + field_max if field_max is not None else None
                    return (result_min, result_max)
                elif value_expr.op == operator.sub:
                    # value = constant - field
                    result_min = constant_val - field_max if field_max is not None else None
                    result_max = constant_val - field_min if field_min is not None else None
                    return (result_min, result_max)
    
    return None

def solve(expression, entry, params, context, value):
    """Solve an expression given the result and the input parameters using Z3.

    This function replaces the original custom constraint solver with Z3,
    providing more robust and powerful constraint solving capabilities.
    
    Key improvements over the original solver:
    - Can solve complex expressions that the original solver couldn't handle
    - Uses Z3 SMT solver for mathematically sound constraint solving
    - Respects field constraints (Minimum/Maximum) when solving
    - May find different but equally valid solutions compared to original
    
    expression -- A bdec.expression.Expression instance to solve.
    params -- A bdec.param.ExpressionParameters instance used to query all
        values passed into the expression.
    value -- The integer value to use when solving the expression.
    context -- A dict of (name:value) representing all known parameter
        values that can be used for solving.
    result -- Returns a dict of {ReferenceExpression: value} """
    
    # Create Z3 solver
    solver = z3.Solver()
    vars_map = {}
    
    try:
        # Convert expression to Z3
        z3_expr = _expression_to_z3(expression, vars_map, context)
        
        # Add constraint that expression equals the target value
        solver.add(z3_expr == value)
        
        # Extract and add field constraints
        field_constraints = _extract_field_constraints(entry, params)
        for param_name, (min_val, max_val) in field_constraints.items():
            if param_name in vars_map:
                z3_var = vars_map[param_name]
                if min_val is not None:
                    solver.add(z3_var >= min_val)
                if max_val is not None:
                    solver.add(z3_var <= max_val)
        
        # Check if solvable
        if solver.check() == z3.sat:
            model = solver.model()
            result = {}
            
            # Extract solutions for each unknown variable
            ref_exprs = _get_reference_expressions(expression)
            for ref_expr in ref_exprs:
                param_name = ref_expr.param_name()
                if param_name in vars_map:
                    z3_var = vars_map[param_name]
                    if z3_var in model:
                        val = model[z3_var].as_long()
                        result[ref_expr] = val
                    else:
                        # Variable exists but no value in model - might be unconstrained
                        # Try to get any valid value
                        val = model.evaluate(z3_var, model_completion=True).as_long()
                        result[ref_expr] = val
            
            return result
        else:
            raise UnsolvableExpressionError(entry, expression, value)
            
    except Exception as e:
        if isinstance(e, (SolverError, UnsolvableExpressionError)):
            raise
        raise SolverError(entry, expression, f'Z3 solver error: {str(e)}')

