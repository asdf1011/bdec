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

from bdec.entry import UndecodedReferenceError, NotEnoughContextError
from bdec.inspect.solver import solve

class DataLengthError(bdec.DecodeError):
    """Encoded data has the wrong length."""
    def __init__(self, entry, expected, actual):
        bdec.DecodeError.__init__(self, entry)
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return "%s expected length %i, got length %i" % (self.entry, self.expected, self.actual)

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
    def __init__(self, name, encoder, passed_params):
        self.name = name
        self.encoder = encoder

        # The in & out parameter directions are reveresed for encoding
        self.inputs = list(p for p in passed_params if p.direction == p.OUT)
        self.outputs = list(p for p in passed_params if p.direction == p.IN)

    def __str__(self):
        return str(self.encoder)


class EntryEncoder:
    def __init__(self, entry, params):
        self.entry = entry
        self.children = []

        # When encoding, the direction of the parameters is inverted. What
        # would usually be an output, is now an input.
        self.inputs = [p for p in params.get_params(entry) if p.direction == p.OUT]
        self.outputs = [p for p in params.get_params(entry) if p.direction == p.IN]
        self._params = params

    def _get_context(self, query, parent, offset):
        # This interface isn't too good; it requires us to load the _entire_ document
        # into memory. This is because it supports 'searching backwards', plus the
        # reference to the root element is kept. Maybe a push system would be better?
        #
        # Problem is, push doesn't work particularly well for bdec.output.instance, nor
        # for choice entries (where we need to re-wind...)
        try:
            return query(parent, self.entry, offset)
        except MissingInstanceError:
            if self.entry.is_hidden():
                return None
            raise

    def _encode(self, query, value):
        """
        Encode a data source, with the context being the data to encode.
        """
        raise NotImplementedError()

    def _encode_child(self, child, query, value, offset, context):
        child_context = {}
        assert len(child.inputs) == len(child.encoder.inputs)
        for our_param, child_param in zip(child.inputs, child.encoder.inputs):
            # Update the child with its required parameters
            child_context[child_param.name] = context[our_param.name]

        for data in child.encoder.encode(query, value, offset, child_context, child.name):
            yield data

        assert len(child.outputs) == len(child.encoder.outputs), \
                'Child has %s outputs, we expected %s' % (child.encoder.outputs, child.outputs)
        for our_param, child_param in zip(child.outputs, child.encoder.outputs):
            # Update our context with the child's outputs...
            context[our_param.name] = child_context[child_param.name]

    def _fixup_value(self, value):
        """
        Allow entries to modify the value to be encoded.
        """
        return value

    def encode(self, query, value, offset, context, name):
        """Return an iterator of bdec.data.Data instances.

        query -- Function to return a value to be encoded when given an entry
          instance and the parent entry's value. If the parent doesn't contain
          the expected instance, MissingInstanceError should be raised.
        value -- This entry's value that is to be encoded.
        """
        encode_length = 0
        value = self._get_context(query, value, offset)
        value = self._fixup_value(value)
        if value is None:
            # We are hidden; get the value from the context.
            value = context[name]

        for constraint in self.entry.constraints:
            constraint.check(self.entry, value, context)

        for data in self._encode(query, value, context):
            encode_length += len(data)
            yield data

        length = None
        if self.entry.length is not None:
            ref_values = solve(self.entry.length, self.entry, self._params, encode_length)
            for ref, ref_value in ref_values.items():
                context[ref.name] = ref_value

            try:
                length = self.entry.length.evaluate(context)
            except UndecodedReferenceError, ex:
                raise NotEnoughContextError(self.entry)

        if length is not None and encode_length != length:
            raise DataLengthError(self.entry, length, encode_length)

    def __str__(self):
        return 'encoder for %s' % self.entry
