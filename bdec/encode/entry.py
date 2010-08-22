#   Copyright (C) 2008-2009 Henry Ludemann
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

import bdec

from bdec.data import Data
from bdec.choice import Choice
from bdec.entry import UndecodedReferenceError, NotEnoughContextError, is_hidden
from bdec.field import Field
from bdec.sequence import Sequence
from bdec.sequenceof import SequenceOf
from bdec.inspect.solver import solve, SolverError

class DataLengthError(bdec.DecodeError):
    """Encoded data has the wrong length."""
    def __init__(self, entry, expected, actual):
        bdec.DecodeError.__init__(self, entry)
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return "%s expected length %s, got length %i" % (self.entry, self.expected, self.actual)

class MissingInstanceError(bdec.DecodeError):
    """
    Error raised during encoding when a parent object doesn't have a named child object.
    """
    def __init__(self, parent, child):
        bdec.DecodeError.__init__(self, child)
        self.parent = parent
        self.child = child

    def __str__(self):
        return "object '%s' doesn't have child object '%s'" % (self.parent, self.child.name)

class Child:
    def __init__(self, child, encoder, passed_params, is_hidden):
        self.name = child.name
        self.child = child
        self.encoder = encoder
        self.params = list(passed_params)
        self.is_hidden = is_hidden

    def __repr__(self):
        return "'%s' %s" % (self.name, str(self.encoder))

class MockSequenceValue(dict):
    def __int__(self):
        return 0

    def __eq__(self, other):
        return isinstance(other, MockSequenceValue)

def _mock_query(parent, entry, offset, name):
    """A mock query object to return data for hidden common entries.

    It will return null data for fields, etc."""
    if isinstance(parent, (int, long)) or parent is None:
        raise MissingInstanceError(parent, entry)

    try:
        return parent[name]
    except KeyError:
        pass

    # Check to see if it's a compound name...
    result = {}
    for param, value in parent.items():
        names = param.split('.')
        if names[0] == name:
            child_name = '.'.join(names[1:])
            result[child_name] = value
    if result:
        return result

    if is_hidden(entry.name):
        raise MissingInstanceError(parent, entry)

    # We have to return some suitable data for these entries; return a null
    # data object.
    if isinstance(entry, Field):
        length = entry.length.evaluate({})
        if entry.format == Field.INTEGER:
            return 0
        elif entry.format == Field.TEXT:
            return ''
        elif entry.format == Field.FLOAT:
            return 0.0
        else:
            return Data('\x00' * (length / 8 + 1), length)
    elif isinstance(entry, Sequence):
        return MockSequenceValue()
    elif isinstance(entry, SequenceOf):
        return []
    elif isinstance(entry, Choice):
        return {}
    else:
        raise NotImplementedError('Unknown entry %s to mock data for...' % entry)

class EntryEncoder:
    def __init__(self, entry, expression_params, params, is_hidden):
        self.entry = entry
        self.children = []
        self.is_hidden = is_hidden

        # When encoding, the direction of the parameters is inverted. What
        # would usually be an output, is now an input.
        self.params = params
        self._params = expression_params
        self._is_length_referenced = expression_params.is_length_referenced(entry)
        self._is_value_referenced = expression_params.is_value_referenced(entry)

    def _solve(self, expression, value, context):
        '''Solve an expression given the result and context.

        Will throw a bdec.inspect.solver.SolverError if the expression cannot
        be resolved correctly.'''
        ref_values = solve(expression, self.entry, self._params, context, value)

        for ref, ref_value in ref_values.items():
            context[ref.name] = ref_value

    def _get_value(self, query, parent, offset, name, context):
        # This interface isn't too good; it requires us to load the _entire_ document
        # into memory. This is because it supports 'searching backwards', plus the
        # reference to the root element is kept. Maybe a push system would be better?
        #
        # Problem is, push doesn't work particularly well for bdec.output.instance, nor
        # for choice entries (where we need to re-wind...)
        try:
            return query(parent, self.entry, offset, name)
        except MissingInstanceError:
            if not self.is_hidden:
                raise
            try:
                # This is a hidden entry; it's value may be stored in the parameter
                # context.
                return context[self.entry.name]
            except KeyError:
                return None

    def _encode(self, query, value, context):
        """
        Encode a data source, with the context being the data to encode.
        """
        raise NotImplementedError()

    def _encode_child(self, child, query, value, offset, context):
        child_context = {}
        should_use_mock = (self.is_hidden or child.is_hidden) and not child.encoder.is_hidden
        if should_use_mock:
            # The child entry is hidden, but the parent is visible; create a
            # 'mock' child entry suitable for encoding. This must contain any
            # objects that are passed in. We use the context, as this contains
            # the required data for this hidden entry.
            query = _mock_query
            value = context.copy()

        for our_param, child_param in zip(child.params, child.encoder.params):
            if child_param.direction == our_param.IN:
                try:
                    child_context[child_param.name] = context[our_param.name]
                except KeyError:
                    # When encoding, output value references become input
                    # references, but these are not necessarily populated
                    # everywhere. In these cases we'll populate them with None...
                    child_context[child_param.name] = None

        child_value = child.encoder.get_value(query, value, offset, child.name, child_context)
        for data in child.encoder.encode(query, child_value, offset, child_context, child.name):
            yield data

        for our_param, child_param in zip(child.params, child.encoder.params):
            if child_param.direction == our_param.OUT:
                # Update our context with the child's outputs...
                context[our_param.name] = child_context[child_param.name]

    def _fixup_value(self, value, context):
        """
        Allow entries to modify the value to be encoded.
        """
        return value

    def get_value(self, query, value, offset, name, context):
        try:
            value = self._get_value(query, value, offset, name, context)
        except MissingInstanceError:
            if not self.is_hidden:
                raise
            value = None
        return self._fixup_value(value, context)

    def encode(self, query, value, offset, context, name):
        """Return an iterator of bdec.data.Data instances.

        query -- Function to return a value to be encoded when given an entry
          instance and the parent entry's value. If the parent doesn't contain
          the expected instance, MissingInstanceError should be raised.
        value -- This entry's value that is to be encoded.
        """

        encode_length = 0

        for constraint in self.entry.constraints:
            constraint.check(self.entry, value, context)

        for data in self._encode(query, value, context):
            encode_length += len(data)
            yield data

        length = encode_length
        if self.entry.length is not None:
            # Check that the expression length matches the 'real' length
            try:
                self._solve(self.entry.length, encode_length, context)
            except SolverError, ex:
                raise DataLengthError(self.entry, ex.expr, ex.expected)
        if self._is_length_referenced:
            context[self.entry.name + ' length'] = length
        if self._is_value_referenced:
            context[self.entry.name] = int(value)

    def __repr__(self):
        return 'encoder for %s' % self.entry

