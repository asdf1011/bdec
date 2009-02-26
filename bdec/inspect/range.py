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

"""A class for representing the range of values for a variable.

The 'range' can be multiplied, divided, added, etc to determine the correct
range.
"""
import decimal

class _Infinite:
    def __mul__(self, other):
        if other == 0:
            return 0
        if not _is_positive(other):
            return _MinusInfinite()
        return self

    def __rmul__(self, other):
        return self.__mul__(other)

    def __cmp__(self, other):
        if isinstance(other, _Infinite):
            return 0
        return 1


class _MinusInfinite:
    def __mul__(self, other):
        if other == 0:
            return 0
        if not _is_positive(other):
            return _Infinite()
        return self

    def __rmul__(self, other):
        return self.__mul__(other)

    def __cmp__(self, other):
        if isinstance(other, _MinusInfinite):
            return 0
        return -1


def _is_positive(number):
    if isinstance(number, _Infinite):
        return True
    if isinstance(number, _MinusInfinite):
        return False
    return number >= 0


class Range:
    """A range of possible values.

    The range is inclusive. eg: min <= value <= max. If min or max is None, it
    means there is no bound in that direction.
    """
    def __init__(self, min=None, max=None):
        self.min = min
        self.max = max

    def intersect(self, other):
        """Return the intesection of self and other."""
        result = Range()
        # max of None and X will always return X
        result.min = max(self.min, other.min)
        if self.max is not None:
            if other.max is not None:
                result.max = min(self.max, other.max)
            else:
                result.max = self.max
        else:
            result.max = other.max
        return result

    def union(self, other):
        """Return the outer bounds of self and other."""
        result = Range()
        # min of None and X will always return None
        result.min = min(self.min, other.min)
        if self.max is not None and other.max is not None:
            result.max = max(self.max, other.max)
        return result

    def __eq__(self, other):
        return self.min == other.min and self.max == other.max

    def __repr__(self):
        return "[%s, %s]" % (self.min, self.max)

    def __add__(self, other):
        if self.min is None or other.min is None:
            min = None
        else:
            min = self.min + other.min
        if self.max is None or other.max is None:
            max = None
        else:
            max = self.max + other.max
        return Range(min, max)

    def __sub__(self, other):
        if self.min is None or other.max is None:
            min = None
        else:
            min = self.min - other.max
        if self.max is None or other.min is None:
            max = None
        else:
            max = self.max - other.min
        return Range(min, max)

    def __mul__(self, other):
        minx = self.min if self.min is not None else _MinusInfinite()
        maxx = self.max if self.max is not None else _Infinite()
        miny = other.min if other.min is not None else _MinusInfinite()
        maxy = other.max if other.max is not None else _Infinite()

        values = []
        values.append(minx * miny)
        values.append(minx * maxy)
        values.append(maxx * miny)
        values.append(maxx * maxy)

        values.sort()
        min = values[0] if isinstance(values[0], (int, long)) else None
        max = values[3] if isinstance(values[3], (int, long)) else None
        return Range(min, max)

    def __div__(self, other):
         # Instead of implementing division, we'll just figure out the inverse,
         # and multiply the two together.
        if other.min == 0:
            miny = _Infinite()
        elif other.min is None:
            miny = 0
        else:
            miny = 1 / decimal.Decimal(other.min)

        if other.max == 0:
            maxy = _Infinite()
        elif other.min is None:
            maxy = 0
        else:
            maxy = 1 / decimal.Decimal(other.max)

        minx = self.min if self.min is not None else _MinusInfinite()
        maxx = self.max if self.max is not None else _Infinite()

        values = []
        values.append(minx * miny)
        values.append(minx * maxy)
        values.append(maxx * miny)
        values.append(maxx * maxy)

        values.sort()
        min = int(values[0]) if isinstance(values[0], decimal.Decimal) else None
        max = int(values[3]) if isinstance(values[3], decimal.Decimal) else None
        return Range(min, max)

    def __mod__(self, other):
        if other.max is not None:
            # FIXME: This assumes 'a % b' returns a postive integer; this isn't
            # true for all languages. What do we do?
            return Range(0, other.max - 1)
        if self.max is not None:
            if other.max is None or self.max < other.max:
                return Range(0, self.max)
        return Range(0, other.max)

    def __lshift__(self, other):
        return Range(self.min << other.min, self.max << other.max)

    def __rshift__(self, other):
        return Range(self.min >> other.max, self.max >> other.min)

