#   Copyright (C) 2009 Henry Ludemann
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

from bdec.expression import compile, Constant, Delayed, UndecodedReferenceError
from bdec.field import Field
from bdec.sequence import Sequence

class Integers:
    """
    Class for generating integer entry decoders.
    """
    def __init__(self):
        self.common = {}

    def _variable_length_signed_big_endian(self, length):
        # FIXME: We could perhaps add a shift '<<' operator?
        raise NotImplementedError()

    def signed_big_endian(self, length_expr):
        try:
            length = length_expr.evaluate({})
        except UndecodedReferenceError:
            return self._variable_length_signed_big_endian(length_expr)

        name = 'integer %i' % length
        try:
            result = self.common[name]
        except KeyError:
            is_signed = Field('signed:', 1)
            value = Field('value:', length - 1)
            minimum = pow(2, length - 1)
            # We define the minimum as being '-number - 1' to avoid compiler
            # warnings in C, where there are no negative constants, just
            # constants that are then negated (and the positive version of
            # the constant may be too big a number).
            expression = compile('${signed:} * (0 - %i - 1) + ${value:}' % (minimum - 1))
            result = Sequence(name, [is_signed, value], value=expression)
            self.common[name] = result
        return result

