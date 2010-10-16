#   Copyright (C) 2010 Henry Ludemann
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

"""
Classes for defining higher level integer encodings in a low level representation.
"""

import operator

from bdec.choice import Choice
from bdec.expression import compile, Constant, ArithmeticExpression, UndecodedReferenceError
from bdec.field import Field
from bdec.sequence import Sequence

class IntegerError(Exception):
    pass

class Integers:
    """
    Class for generating integer entry decoders.
    """
    def __init__(self):
        self.common = {}

    def signed_big_endian(self, length_expr):
        try:
            # We try to choose the name based on the length value. If we
            # cannot evaluate the length, we'll use the length name.
            name = 'big endian integer %s' % length_expr.evaluate({})
        except UndecodedReferenceError:
            name = 'big endian integer %s' % length_expr

        try:
            result = self.common[name]
        except KeyError:
            is_signed = Field('signed:', 1)
            value = Field('integer value:', ArithmeticExpression(operator.sub, length_expr, Constant(1)))
            expression = compile('${signed:} * ((0 - 1) << (%s - 1)) + ${integer value:}' % (length_expr))
            result = Sequence(name, [is_signed, value], value=expression)
            self.common[name] = result
        return result

    def _variable_length_signed_little_endian(self, length_expr):
        name = 'variable length integer'
        try:
            result = self.common[name]
        except KeyError:
            options = [
                    self.signed_litte_endian(Constant(32)),
                    self.signed_litte_endian(Constant(24)),
                    self.signed_litte_endian(Constant(16)),
                    self.signed_litte_endian(Constant(8)),
                    ]
            # We wrap the choice inside a sequence, as choices don't currently
            # 'compile' to integers (and sequences do).
            var_name = 'variable integer types:'
            result = Sequence(name, [Choice(var_name, options)],
                    value=compile('${%s}' % var_name))
            self.common[name] = result
        return result

    def signed_litte_endian(self, length_expr):
        try:
            length = length_expr.evaluate({})
        except UndecodedReferenceError:
            return self._variable_length_signed_little_endian(length_expr)

        if length % 8 != 0:
            raise IntegerError('The length of little endian fields must be a multiple of 8.')

        name = 'little endian integer %s' % length
        try:
            result = self.common[name]
        except KeyError:
            children = []
            num_bytes = length / 8
            for i in range(num_bytes - 1):
                children.append(Field('byte %i:' % i, 8))
            children.append(Field('signed:', 1))
            children.append(Field('byte %i:' % (num_bytes - 1), 7))
            # We define the minimum as being '-number - 1' to avoid compiler
            # warnings in C, where there are no negative constants, just
            # constants that are then negated (and the positive version of
            # the constant may be too big a number).
            maximum = 1 << (length - 1)
            names = ['${byte %i:}' % i for i in range(num_bytes)]
            names.reverse()
            reference = reduce(lambda left, right: '(%s) * 256 + %s' % (left, right), names)
            value_text = '${signed:} * (0 - %i - 1) + %s' % (maximum - 1, reference)
            result = Sequence(name, children, value=compile(value_text))
            self.common[name] = result
        return result

