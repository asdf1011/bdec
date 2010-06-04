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

import operator

from bdec import DecodeError
from bdec.expression import Expression, Constant, UndecodedReferenceError
from bdec.inspect.range import Range

class ConstraintError(DecodeError):
    def __init__(self, entry, actual, comparison, limit):
        DecodeError.__init__(self, entry)
        self._error = '%s %s %s' % (str(actual), comparison, str(limit))

    def __str__(self):
        return '%s constaint failed; %s' % (self.entry, self._error)

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
            raise ConstraintError(entry, int(value), '<', expected)

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
            raise ConstraintError(entry, int(value), '>', expected)

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
                raise ConstraintError(entry, int(value), '!=', expected)
        else:
            if value !=  expected:
                raise ConstraintError(entry, value, '!=', expected)

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
                raise ConstraintError(entry, int(value), '==', expected)
        else:
            if value !=  expected:
                raise ConstraintError(entry, value, '==', expected)

    def range(self):
        limit = _limit(self.limit)
        return Range(limit, limit)

