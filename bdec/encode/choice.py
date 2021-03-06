#   Copyright (C) 2008-2013 Henry Ludemann
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

import logging

from bdec import DecodeError
from bdec.constraints import Equals, Minimum, Maximum
from bdec.encode.entry import EntryEncoder, MissingInstanceError
from bdec.expression import ReferenceExpression, ArithmeticExpression
from bdec.sequence import Sequence
from bdec.inspect.range import Range, Ranges
from bdec.inspect.solver import solve_expression, SolverError

def _get_unpopulated_outputs(choice, child, expression_params):
    """Find all outputs of other children that aren't outputs of child.

    Returns a {name : params}."""
    outputs = [p.name for p in expression_params.get_params(choice)]
    known = [p.name for p in expression_params.get_passed_variables(choice, child)]
    result = {}
    for c in choice.children:
        for p in expression_params.get_passed_variables(choice, c):
            if p.direction == p.OUT and p.name not in known and p.name in outputs:
                result.setdefault(p.name, []).append(p)
    return result

def _is_using_param(expr, param_name):
    if isinstance(expr, ReferenceExpression):
        return expr.name == param_name
    elif isinstance(expr, ArithmeticExpression):
        return _is_using_param(expr.left, param_name) or _is_using_param(expr.left, param_name)
    return False

def _solve(result_expr, sequence, param_name, expression_params):
    constant, components = solve_expression(result_expr, sequence.value, sequence, expression_params.expression_params, [])
    if len(components) == 1:
        reference, expression, inverted = components[0]
        if reference.name == param_name:
            return inverted.evaluate({})
        else:
            logging.warning("Expected to solve reference to '%s', but "
                    "found '%s'! Skipping constraint." %
                    (param_name, reference.name))
    else:
        logging.warning("Found multiple unknowns when solving '%s'! Skipping constraint." % sequence.value)

def _get_ranges(entry, param_name, expression_params):
    """ Get the ranges that param_name can be used for. """
    if isinstance(entry, Sequence) and entry.value is not None and \
            _is_using_param(entry.value, param_name):
        # This entry is using the specified parameter; we want to find
        # what values it expects it to be.
        for constraint in entry.constraints:
            value = _solve(constraint.limit, entry, param_name, expression_params)
            if isinstance(constraint, Equals):
                yield Range(value, value)
            elif isinstance(constraint, Maximum):
                yield Range(None, value)
            elif isinstance(constraint, Minimum):
                yield Range(value, None)

    # Look in the children to see if a child entry uses the constraint...
    for child in entry.children:
        for local, param in zip(
                expression_params.get_passed_variables(entry, child),
                expression_params.get_params(child.entry)):
            if local.name == param_name:
                # We pass this parameter into the child. Recurse inwards...
                for r in _get_ranges(child.entry, param.name, expression_params):
                    yield r
                break

def get_default_option_params(choice, child, expression_params, encode_expression_params):
    """Create a dictionary containing default values for output parameters
    that aren't used by this option.

    Returns a {param_name: value} dictionary."""
    result = {}
    outputs = _get_unpopulated_outputs(choice, child, encode_expression_params)
    for name, params in outputs.items():
        # Find the possible range of source values, and intersect it with
        # the constraints placed on it by other earlier children.
        possible = Ranges(p.type.range(expression_params) for p in params)
        for c in choice.children[:choice.children.index(child)]:
            for r in _get_ranges(c.entry, name, encode_expression_params):
                possible.remove(r)
        result[name] = possible.get_default()
    return result

class ChoiceEncoder(EntryEncoder):
    def _get_value(self, query, parent, offset, name, context):
        try:
            return query(parent, self.entry, offset, name)
        except MissingInstanceError:
            # Choice entries can be completely hidden
            return parent


    def _encode(self, query, value, context):
        # We attempt to encode all of the embedded items, until we find
        # an encoder capable of doing it. We try the visible items first, as
        # the hidden entries will usually succeed regardless.
        visible = [c for c in self.children if not c.is_hidden]
        hidden = [c for c in self.children if c.is_hidden]
        children = sorted(self.children, key=lambda c:c.is_hidden)

        best_guess = None
        best_guess_value = None
        for child in children:
            try:
                bits_encoded = 0
                num_entries = [0]
                def mock_query(obj, child, i, name):
                    result = query(obj, child, i, name)
                    num_entries[0] += 1
                    return result
                for data in self._encode_child(child, mock_query, value, 0, context):
                    bits_encoded += len(data)

                # We successfully encoded the entry!
                best_guess = child
                break
            except DecodeError:
                rating = (bits_encoded, num_entries[0])
                if best_guess is None or rating > best_guess_value:
                    best_guess = child
                    best_guess_value = rating

        result = self._encode_child(best_guess, query, value, 0, context)
        context.update(get_default_option_params(self.entry, best_guess.child, self._params, self._encode_expression_params))
        return result
