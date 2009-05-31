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

"""A set of classes for determining the types and range of entry parameters.
"""

import decimal
import operator

from bdec.expression import Delayed, Constant, ValueResult, LengthResult


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
        min = values[0] if isinstance(values[0], int) else None
        max = values[3] if isinstance(values[3], int) else None
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


def _delayed_range(delayed, entry, parameters):
    left = _range(delayed.left, entry, parameters)
    right = _range(delayed.right, entry, parameters)
    return delayed.op(left, right)

def _constant_range(constant, entry, parameters):
    return Range(int(constant.value), int(constant.value))

def _get_param(entry, name, parameters):
    """Get the parameter 'input' to entry with a given name."""
    for param in parameters.get_params(entry):
        if param.name == name:
            return param
    # The param wasn't passed _into_ this entry; check to see if it comes out
    # of one of its children...
    for child in entry.children:
        for param in parameters.get_passed_variables(entry, child):
            if param.name == name:
                return param
    raise Exception("Failed to find parameter '%s' in params for entry '%s'!" % (name, entry))

def _reference_value_range(value, entry, parameters):
    return _get_param(entry, value.name, parameters).type.range(parameters)

def _reference_length_range(value, entry, parameters):
    name = value.name + ' length'
    return _get_param(entry, name, parameters).type.range(parameters)

_handlers = {
        Constant: _constant_range,
        Delayed: _delayed_range,
        ValueResult: _reference_value_range,
        LengthResult: _reference_length_range,
        }

def _range(expression, entry=None, parameters=None):
    """Return a Range instance representing the possible ranges of the expression.

    exression -- The expression to calculate the  range for.
    entry -- The entry where this expression is used. All ValueResult and
        LengthResult names are relative to this entry.
    parameters -- A bdec.inspect.param.ExpressionParameters instance, used to
        calculate the ranges of referenced entries."""
    result = _handlers[expression.__class__](expression, entry, parameters)
    return result


class VariableType:
    """Base class for all parameter types."""
    def __hash__(self):
        return hash(self.__class__)


class EntryType(VariableType):
    """Parameter value whose source is another entry."""
    def __init__(self, entry):
        self.entry = entry

    def __hash__(self):
        return hash(self.entry)

    def __eq__(self, other):
        if not isinstance(other, EntryType):
            return False
        return other.entry is self.entry


class IntegerType(VariableType):
    """Base class for describing the type of an integer."""
    def range(self, parameters):
        """Return a bdec.inspect.range.Range instance indicating the range of valid values."""
        raise NotImplementedError()


class ShouldEndType(IntegerType):
    """Parameter used to pass the 'should end' up to the parent."""
    def __eq__(self, other):
        return isinstance(other, ShouldEndType)

    def range(self, parameters):
        return Range(0, 1)


class EntryLengthType(IntegerType):
    """Parameter value whose source is the length of another entry."""
    def __init__(self, entry):
        self.entry = entry

    def __hash__(self):
        return hash(self.entry)

    def __eq__(self, other):
        return isinstance(other, EntryLengthType) and self.entry is other.entry

    def __repr__(self):
        return 'len{%s}' % self.entry

    def range(self, parameter):
        if self.entry.length is None:
            # We don't know how long this entry is.
            # TODO: We could try examining its children...
            return Range(0, None)
        return _range(self.entry.length, self.entry ,parameter)


class EntryValueType(IntegerType):
    """Parameter value whose source is the integer value of another entry."""
    def __init__(self, entry):
        self.entry = entry

    def __hash__(self):
        return hash(self.entry)

    def __eq__(self, other):
        return isinstance(other, EntryValueType) and self.entry is other.entry

    def range(self, parameters):
        import bdec.choice as chc
        import bdec.field as fld
        import bdec.sequence as seq
        if isinstance(self.entry, fld.Field):
            length_range = _range(self.entry.length, self.entry, parameters)
            result = Range(0, pow(2, length_range.max) - 1)
        elif isinstance(self.entry, seq.Sequence):
            result = _range(self.entry.value, self.entry, parameters)
        elif isinstance(self.entry, chc.Choice):
            ranges = [EntryValueType(child.entry).range(parameters) for child in self.entry.children]
            result = reduce(Range.union, ranges)
        else:
            raise NotImplementedError("Don't know how to query the value range of entry '%s'!'" % self.entry)

        for constraint in self.entry.constraints:
            result = result.intersect(constraint.range())
        return result


class MultiSourceType(IntegerType):
    """Parameter whose value comes from multiple locations."""
    def __init__(self, sources):
        for source in sources:
            assert isinstance(source, VariableType)
        self.sources = sources

    def __eq__(self, other):
        if not isinstance(other, MultiSourceType):
            return False
        if len(self.sources) != len(other.sources):
            return False
        for a, b in zip(self.sources, other.sources):
            if a != b:
                return False
        return True

    def range(self, parameters):
        ranges = (source.range(parameters) for source in self.sources)
        return reduce(Range.union, ranges)

