#   Copyright (C) 2008-2010 Henry Ludemann
#   Copyright (C) 2010 PRESENSE Technologies GmbH
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

import logging

from bdec import DecodeError
from bdec.constraints import Equals, Minimum, Maximum
from bdec.encode.entry import EntryEncoder, MissingInstanceError
from bdec.expression import ReferenceExpression
from bdec.sequence import Sequence
from bdec.inspect.range import Range, Ranges
from bdec.inspect.solver import solve_expression, SolverError

class ChoiceEncoder(EntryEncoder):
    def _get_value(self, query, parent, offset, name, context):
        try:
            return query(parent, self.entry, offset, name)
        except MissingInstanceError:
            # Choice entries can be completely hidden
            return parent

    def _get_unpopulated_outputs(self, child):
        """Find all outputs of other children that aren't outputs of child.

        Returns a {name : params}."""
        known = [p.name for p in child.params]
        result = {}
        for c in self.children:
            for p in c.params:
                if p.direction == p.OUT and p.name not in known:
                    result.setdefault(p.name, []).append(p)
        return result

    def _is_using_param(self, expr, param_name):
        if isinstance(expr, ReferenceExpression):
            return expr.name == param_name
        elif isinstance(expr, ArithmeticExpression):
            return self._is_using_param(expr.left, param_name) or self._is_using_param(expr.left, param_name)
        return False

    def _solve(self, result_expr, sequence, param_name):
        constant, components = solve_expression(result_expr, sequence.value, sequence, self._params, [])
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

    def _get_ranges(self, entry, param_name):
        """ Get the ranges that param_name can be used for. """
        if isinstance(entry, Sequence) and entry.value is not None and \
                self._is_using_param(entry.value, param_name):
            # This entry is using the specified parameter; we want to find
            # what values it expects it to be.
            for constraint in entry.constraints:
                value = self._solve(constraint.limit, entry, param_name)
                if isinstance(constraint, Equals):
                    yield Range(value, value)
                elif isinstance(constraint, Maximum):
                    yield Range(None, value)
                elif isinstance(constraint, Minimum):
                    yield Range(value, None)

        # Look in the children to see if a child entry uses the constraint...
        for child in entry.children:
            for local, param in zip(
                    self._params.get_passed_variables(entry, child),
                    self._params.get_params(child.entry)):
                if local.name == param_name:
                    # We pass this parameter into the child. Recurse inwards...
                    for r in self._get_ranges(child.entry, param.name):
                        yield r
                    break

    def _create_mock_out_params(self, child):
        """Create a context variable containing any mocked output parameters."""
        result = {}
        outputs = self._get_unpopulated_outputs(child)
        for name, params in outputs.items():
            # Find the possible range of source values, and intersect it with
            # the constraints placed on it by other earlier children.
            possible = Ranges(p.type.range(self._params) for p in params)
            for c in self.children[:self.children.index(child)]:
                for r in self._get_ranges(c.encoder.entry, name):
                    possible.remove(r)

            # Use the possible value closest to zero.
            positive = Range(0, None)
            negative = Range(None, 0)
            if possible.intersect(positive):
                value = possible.intersect(positive)[0].min
            elif possible.intersect(negative):
                value = possible.intersect(positive)[-1].max
            else:
                value = 0
                logging.warning('Unable to choose a good output for %s; using %s', name, value)
            result[name] = value
        return result

    def _encode(self, query, value, context):
        # We attempt to encode all of the embedded items, until we find
        # an encoder capable of doing it. We try the visible items first, as
        # the hidden entries will usually succeed regardless.
        visible = [c for c in self.children if not c.is_hidden]
        hidden = [c for c in self.children if c.is_hidden]
        children = sorted(self.children, key=lambda c:c.is_hidden)

        best_guess = None
        best_guess_bits = 0
        for child in children:
            try:
                bits_encoded = 0
                for data in self._encode_child(child, query, value, 0, context):
                    bits_encoded += len(data)

                # We successfully encoded the entry!
                best_guess = child
                break
            except DecodeError:
                if best_guess is None or bits_encoded > best_guess_bits:
                    best_guess = child
                    best_guess_bits = bits_encoded

        result = self._encode_child(best_guess, query, value, 0, context)
        context.update(self._create_mock_out_params(best_guess))
        return result
