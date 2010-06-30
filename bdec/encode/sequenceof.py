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

from bdec import DecodeError
from bdec.encode.entry import EntryEncoder
from bdec.inspect.solver import solve

class InvalidSequenceOfCount(DecodeError):
    """Raised during encoding when an invalid length is found."""
    def __init__(self, seq, expected, actual):
        DecodeError.__init__(self, seq)
        self.sequenceof = seq
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return "%s expected count of %i, got %i" % (self.sequenceof, self.expected, self.actual)

class SequenceOfEncoder(EntryEncoder):
    def _encode(self, query, value, context):
        count = 0
        for i, child_value in enumerate(value):
            count += 1
            for data in self._encode_child(self.children[0], query, value, i, context):
                yield data

        if self.entry.count:
            # Update the context with the detected parameters
            ref_values = solve(self.entry.count, self.entry, self._params, count)
            for ref, ref_value in ref_values.items():
                context[ref.name] = ref_value

            if self.entry.count.evaluate(context) != count:
                raise InvalidSequenceOfCount(self.entry, self.entry.count.evaluate({}), count)