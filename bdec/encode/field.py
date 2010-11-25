#   Copyright (C) 2008-2010 Henry Ludemann
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
from bdec.data import Data, DataError
from bdec.field import Field, FieldDataError, BadFormatError, BadEncodingError
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

def _convert_type(entry, data, expected_type):
    try:
        return expected_type(data)
    except:
        raise BadFormatError(entry, data, expected_type)

def convert_value(entry, value, length):
    """Convert a value to the correct type given the entry.

    For example, given an integer field, the string '43' would be converted to
    the number 43."""
    temp_original = value
    if entry.format == Field.BINARY:
        try:
            if isinstance(value, Data):
                value = value.copy()
            elif isinstance(value, int) or isinstance(value, long):
                value = Data.from_int_big_endian(value, int(length))
            else:
                value = Data.from_binary_text(_convert_type(entry, value, str))
        except DataError, ex:
            raise FieldDataError(entry, ex)
    elif entry.format == Field.HEX:
        value = Data.from_hex(_convert_type(entry, value, str))
    elif entry.format == Field.TEXT:
        value = _convert_type(entry, value, str)
    elif entry.format == Field.INTEGER:
        value = _convert_type(entry, value, int)
    elif entry.format == Field.FLOAT:
        value = _convert_type(entry, value, float)
    else:
        raise NotImplementedError(entry, value, context)
    return value

class _ContextLength:
    def __init__(self, length, context):
        self.length = length
        self.context = context

    def __int__(self):
        return self.length.evaluate(self.context)

def convert_value_context(entry, value, context):
    return convert_value(entry, value, _ContextLength(entry.length, context))

def _encode_data(entry, value, length):
    if entry.format in (Field.BINARY, Field.HEX):
        assert isinstance(value, Data)
        result = value.copy()
    elif entry.format == Field.TEXT:
        assert isinstance(value, basestring)
        try:
            result = Data(value.encode(entry.encoding))
        except UnicodeDecodeError:
            raise BadEncodingError(entry, value)
    elif entry.format == Field.INTEGER:
        assert isinstance(value, (int, long))
        if length is None:
            raise FieldDataError(entry, 'Unable to encode integer field '
                    'without explicit length')
        assert entry.encoding in [Field.BIG_ENDIAN, Field.LITTLE_ENDIAN]
        if entry.encoding == Field.BIG_ENDIAN:
            result = Data.from_int_big_endian(value, length)
        else:
            result = Data.from_int_little_endian(value, length)
    elif entry.format == Field.FLOAT:
        assert entry.encoding in [Field.BIG_ENDIAN, Field.LITTLE_ENDIAN]
        assert isinstance(value, float)
        if entry.encoding == Field.BIG_ENDIAN:
            result = Data.from_float_big_endian(value, length)
        else:
            result = Data.from_float_little_endian(value, length)
    else:
        raise Exception("Unknown field format of '%s'!" % entry.format)

    return result

def encode_value(entry, value, length=None):
    """
    Convert an object to a dt.Data object.

    Can raise dt.DataError errors.
    """
    if length is None:
        try:
            length = entry.length.evaluate({})
        except UndecodedReferenceError:
            # The length isn't available...
            pass

    try:
        return _encode_data(entry, value, length)
    except DataError, ex:
        raise FieldDataError(entry, ex)


class FieldEncoder(EntryEncoder):
    def _get_default(self, context):
        # We handle strings as a prompt to use the expected value. This is
        # because the named item may be in the output, but not necessarily
        # the value (eg: in the xml representation, it is clearer to not
        # display the expected value).
        for constraint in self.entry.constraints:
            if isinstance(constraint, Equals):
                value = constraint.limit.evaluate(context)
                if isinstance(value, Data):
                    value = self.entry.decode_value(value)
                if isinstance(value, Data):
                    # This is a binary or hex object. For variable length
                    # fields, it may be that the length of the expected value
                    # doesn't match the required length; in this case we have
                    # to add leading nulls.
                    try:
                        length = self.entry.length.evaluate(context)
                    except UndecodedReferenceError, ex:
                        # We don't know what length it should be. Just make
                        # it a multiple of whole bytes.
                        length = len(value)
                        if length % 8:
                            length = length + (8 - length % 8)
                    value = Data('\x00' * (length / 8 + 1), 0, length - len(value)) + value
                break
        else:
            if self.is_hidden:
                try:
                    length = self.entry.length.evaluate(context)
                except UndecodedReferenceError, ex:
                    # We don't know, and can't calculate, the length; try
                    # making it zero.
                    length = 0
                value = self.entry.decode_value(Data('\x00' * (length / 8 + 1), 0, length))
            else:
                # We don't have a default for this entry
                raise MissingFieldException(self.entry)
        return value

    def _get_data(self, value, context):
        try:
            length = self.entry.length.evaluate(context)
            return encode_value(self.entry, value, length)
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
                        return encode_value(self.entry, value, length)
                    except FieldDataError:
                        # The value didn't fit in this length... try the next
                        # one.
                        pass
                else:
                    raise VariableIntegerTooLongError(self.entry, value)
            else:
                # All other types (eg: string, binary, hex) have an implicit
                # length that the encoder can use.
                return encode_value(self.entry, value, None)

    def _fixup_value(self, value, context):
        original = value
        if value in [None, '']:
            try:
                value = self._get_default(context)
            except MissingFieldException:
                # If we have an empty string for a text field, it's not missing.
                if value is None or self.entry.format != Field.TEXT:
                    raise
        return convert_value_context(self.entry, value, context)

    def _encode(self, query, value, context):
        yield self._get_data(value, context)

