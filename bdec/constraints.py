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

import operator

from bdec import DecodeError
from bdec.data import Data
from bdec.expression import Expression, Constant, UndecodedReferenceError
from bdec.inspect.range import Range

class ConstraintError(DecodeError):
    def __init__(self, entry, actual, comparison, limit):
        DecodeError.__init__(self, entry)
        self._comparision = comparison
        self._expected = limit
        self._actual = actual

    def __str__(self):
        return 'Expected ${%s} %s %s; got %s' % (self.entry.name,
                self._comparision, self._expected, self._actual)

def _limit(expression):
    try:
        return expression.evaluate({})
    except UndecodedReferenceError:
        # We aren't able to determine this limit
        return None

class Minimum:
    def __init__(self, limit):
        if not isinstance(limit, Expression):
            limit = Constant(limit)
        self.limit = limit
        self.type = '<'

    def check(self, entry, value, context):
        expected = self.limit.evaluate(context)
        if isinstance(value, basestring):
            # It is useful to check the bounds of a text character...
            value = ord(value)
        if int(value) < expected:
            raise ConstraintError(entry, int(value), '>=', expected)

    def range(self):
        return Range(_limit(self.limit), None)


class Maximum:
    def __init__(self, limit):
        if not isinstance(limit, Expression):
            limit = Constant(limit)
        self.limit = limit
        self.type = '>'

    def check(self, entry, value, context):
        expected = self.limit.evaluate(context)
        if isinstance(value, basestring):
            # It is useful to check the bounds of a text character...
            value = ord(value)
        if int(value) > expected:
            raise ConstraintError(entry, int(value), '<=', expected)

    def range(self):
        return Range(None, _limit(self.limit))


class Equals:
    def __init__(self, expected):
        if not isinstance(expected, Expression):
            expected = Constant(expected)
        self.limit = expected
        self.type = '!='

    def check(self, entry, value, context):
        expected = self.limit.evaluate(context)
        if isinstance(expected, int):
            if int(value) !=  expected:
                raise ConstraintError(entry, int(value), '==', expected)
        elif isinstance(expected, Data):
            # We aren't checking the length here, only the value (for example,
            # the expected value for a variable length binary field will have
            # a different length than the actual). Only compare the bits that
            # are valid.
            length_diff = len(value) - len(expected)
            if length_diff > 0:
                # The expected value is shorter than the actual, so grow it.
                expected = Data('\x00' * (length_diff / 8 + 1), 0, length_diff) + expected
            elif length_diff < 0:
                # The expected value is longer than the actual, so shrink it.
                shorter = expected.copy()
                leading = shorter.pop(-length_diff)
                if not int(leading):
                    # We can safely pop the leading bits.
                    expected = shorter
            if value !=  expected:
                raise ConstraintError(entry, value, '==', expected)
        else:
            if value !=  expected:
                raise ConstraintError(entry, value, '==', expected)

    def range(self):
        limit = _limit(self.limit)
        return Range(limit, limit)


class NotEquals:
    def __init__(self, expected):
        if not isinstance(expected, Expression):
            expected = Constant(expected)
        self.limit = expected
        self.type = '=='

    def check(self, entry, value, context):
        expected = self.limit.evaluate(context)
        if isinstance(expected, int):
            if int(value) ==  expected:
                raise ConstraintError(entry, int(value), '!=', expected)
        else:
            if value !=  expected:
                raise ConstraintError(entry, value, '!=', expected)

    def range(self):
        limit = _limit(self.limit)
        return Range(limit, limit)

