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
from bdec.constraints import Equals
from bdec.data import Data
from bdec.field import FieldDataError
from bdec.encode.entry import EntryEncoder
from bdec.expression import UndecodedReferenceError
from bdec.inspect.type import expression_range as erange

class MissingFieldException(DecodeError):
    def __str__(self):
        return 'Unknown value when encoding %s.' % self.entry

class VariableIntegerTooLongError(DecodeError):
    def __init__(self, entry, value):
        DecodeError.__init__(self, entry)
        self.value = value

    def __str__(self):
        return '%s is too long to fit in variable length integer %s' % (self.value, self.entry)


class FieldEncoder(EntryEncoder):
    def _fixup_value(self, value, context):
        if value in [None, '']:
            # We handle strings as a prompt to use the expected value. This is
            # because the named item may be in the output, but not necessarily
            # the value (eg: in the xml representation, it is clearer to not
            # display the expected value).
            for constraint in self.entry.constraints:
                if isinstance(constraint, Equals):
                    value = constraint.limit.evaluate(context)
                    if isinstance(value, Data):
                        value = self.entry.decode_value(value)
                    break
            else:
                if self.is_hidden:
                    try:
                        length = self.entry.length.evaluate(context)
                    except UndecodedReferenceError, ex:
                        # We don't know, and can't calculate, the length; try
                        # making it zero.
                        length = 0
                    value = Data('\x00' * (length / 8 + 1), 0, length)
                elif value is None:
                    # Only report an error when we have None; if we have an
                    # empty string here, it's probably just that.
                    raise MissingFieldException(self.entry)

        return value

    def _encode(self, query, value, context):
        try:
            length = self.entry.length.evaluate(context)
            yield self.entry.encode_value(value, length)
        except UndecodedReferenceError, ex:
            # We don't know how long this entry should be.
            if self.entry.format == self.entry.INTEGER:
                # Integers require a specific length of encoding. If one is
                # not specified, we'll try several lengths until we find one
                # that fits.
                #
                # We only consider lengths that are in the range specified by
                # the entry length to avoid choosing an out of bounds length.
                length_range = erange(self.entry.length, self.entry, self._params)
                def is_valid(length):
                    if length_range.min is not None and length_range.min > length:
                        return False
                    if length_range.max is not None and length_range.max < length:
                        return False
                    return True
                possible_lengths = [8, 16, 32, 64]
                for length in (l for l in possible_lengths if is_valid(l)):
                    try:
                        yield self.entry.encode_value(value, length)
                        break
                    except FieldDataError:
                        # The value didn't fit in this length... try the next
                        # one.
                        pass
                else:
                    raise VariableIntegerTooLongError(self.entry, value)
            else:
                # All other types (eg: string, binary, hex) have an implicit
                # length that the encoder can use.
                yield self.entry.encode_value(value, None)

