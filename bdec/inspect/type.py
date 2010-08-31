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

import operator

import bdec.choice as chc
from bdec.constraints import Equals
from bdec.entry import UndecodedReferenceError
from bdec.expression import ArithmeticExpression, Constant, ValueResult, LengthResult
import bdec.field as fld
from bdec.inspect.range import Range
import bdec.sequence as seq


def _delayed_range(delayed, entry, parameters):
    left = expression_range(delayed.left, entry, parameters)
    right = expression_range(delayed.right, entry, parameters)
    return delayed.op(left, right)

def _constant_range(constant, entry, parameters):
    return Range(int(constant.value), int(constant.value))

def _get_param(entry, name, parameters):
    """Get the parameter 'input' to entry with a given name."""
    names = []
    for param in parameters.get_params(entry):
        names.append(param.name)
        if param.name == name and param.direction == param.IN:
            return param
    # The param wasn't passed _into_ this entry; check to see if it comes out
    # of one of its children...
    for child in entry.children:
        for param in parameters.get_passed_variables(entry, child):
            names.append(param.name)
            if param.name == name:
                return param
    if name == entry.name:
        # We are referencing the entry itself (probably from a solve expression)
        from bdec.inspect.param import Param
        return Param(entry.name, Param.OUT, EntryValueType(entry))
    raise Exception("Failed to find parameter '%s' in params for entry '%s'! Found params are %s" % (name, entry, names))

def _reference_range(value, entry, parameters):
    return _get_param(entry, value.param_name(), parameters).type.range(parameters)

_handlers = {
        Constant: _constant_range,
        ArithmeticExpression: _delayed_range,
        ValueResult: _reference_range,
        LengthResult: _reference_range,
        }

def expression_range(expression, entry=None, parameters=None):
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

    def __repr__(self):
        return '(%s)&' % self.entry


class IntegerType(VariableType):
    """Base class for describing the type of an integer."""
    def range(self, parameters):
        """Return a bdec.inspect.range.Range instance indicating the range of valid values."""
        raise NotImplementedError()

    def has_expected_value(self):
        """Is the value referenced by this entry constant or visible."""
        raise NotImplementedError()

class ShouldEndType(IntegerType):
    """Parameter used to pass the 'should end' up to the parent."""
    def __eq__(self, other):
        return isinstance(other, ShouldEndType)

    def range(self, parameters):
        return Range(0, 1)

    def __repr__(self):
        return 'should_end'


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
        return expression_range(self.entry.length, self.entry ,parameter)

    def has_expected_value(self):
        return False


class EntryValueType(IntegerType):
    """Parameter value whose source is the integer value of another entry."""
    def __init__(self, entry):
        self.entry = entry

    def __hash__(self):
        return hash(self.entry)

    def __eq__(self, other):
        return isinstance(other, EntryValueType) and self.entry is other.entry

    def range(self, parameters):
        if isinstance(self.entry, fld.Field):
            length_range = expression_range(self.entry.length, self.entry, parameters)
            # If our length is of a variable range, it can be very large.
            # Attempting to take a power of a large number takes a very long
            # time, is is quite meaningless; limit it to 64 bits.
            max_length = min(length_range.max, 64)
            result = Range(0, pow(2, max_length) - 1)
        elif isinstance(self.entry, seq.Sequence):
            result = expression_range(self.entry.value, self.entry, parameters)
        elif isinstance(self.entry, chc.Choice):
            ranges = [EntryValueType(child.entry).range(parameters) for child in self.entry.children]
            result = reduce(Range.union, ranges)
        else:
            raise NotImplementedError("Don't know how to query the value range of entry '%s'!'" % self.entry)

        for constraint in self.entry.constraints:
            result = result.intersect(constraint.range())
        return result

    def _is_value_known(self, entry):
        for constraint in entry.constraints:
            if isinstance(constraint, Equals):
                return True

        if isinstance(entry, seq.Sequence):
            if entry.value:
                # Check to see if the entry value is constant
                # TODO: We should examine the source parameters of this
                # value, instead of trying to execute it...
                try:
                    entry.value.evaluate({})
                    return True
                except UndecodedReferenceError:
                    pass
            return False
        elif isinstance(entry, chc.Choice):
            for child in entry.children:
                if not self._is_value_known(child.entry):
                    return False
            return True
        return False

    def has_expected_value(self):
        return self._is_value_known(self.entry)

    def __repr__(self):
        return '${%s}' % self.entry


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

    def has_expected_value(self):
        for source in self.sources:
            if not source.has_expected_value():
                return False
        return True

    def __repr__(self):
        return 'coalsce(%s)' % ','.join(str(source) for source in self.sources)

