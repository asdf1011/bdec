#   Copyright (C) 2008-2009 Henry Ludemann
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

"""
The bdec.field module contains the Field class, and all errors related to its
use.
"""

import bdec.data as dt
from bdec.constraints import Equals
import bdec.entry
import bdec.expression

class FieldError(bdec.DecodeError):
    """
    Base class for all field errors.
    """
    def __init__(self, field):
        bdec.DecodeError.__init__(self, field)
        assert isinstance(field, Field)
        self.field = field

    def __str__(self):
        return "%s: %s" % (self.__class__, self.field)


class BadEncodingError(FieldError):
    """Error raised when data couldn't be converted to a text fields encoding."""
    def __init__(self, field, data):
        FieldError.__init__(self, field)
        self.data = data

    def __str__(self):
        return "BadEncodingError: %s couldn't encode %s" % (self.field, self.data)

class BadFormatError(FieldError):
    """Got the wrong sort of data type when encoding. """
    def __init__(self, field, data, expected_type):
        FieldError.__init__(self, field)
        self.data = data
        self.expected_type = expected_type

    def __str__(self):
        return "BadFormatError: %s expected %s got '%s'" % (self.field, self.expected_type, self.data)


class FieldDataError(FieldError):
    """An error with converting the data to or from the specified type. """
    def __init__(self, field, error):
        FieldError.__init__(self, field)
        self.error = error

    def __str__(self):
        return "%s - %s" % (self.field, self.error)

class _ValidatedData(dt.Data):
    """Data that has been validated to exist in the backing stored."""
    def __init__(self, *args):
        dt.Data.__init__(self, *args)
        self.validate()

class _HexData(_ValidatedData):
    """ A data instance that will turn into a hex string. """
    def __str__(self):
        return self.get_hex()

class _BinaryData(_ValidatedData):
    """ A data instance that will turn into a binary string. """
    def __str__(self):
        return self.get_binary_text()


class Field(bdec.entry.Entry):
    """A field represents data found in the binary file.

    A field can be of variable length, be non-byte aligned, be in one of many
    formats and encodings, and can reference previously decoded fields.
    """

    # Field format types
    TEXT = "text"
    INTEGER = "integer"
    HEX = "hex"
    BINARY = "binary"
    FLOAT = "float"

    _formats = [TEXT, INTEGER, HEX, BINARY, FLOAT]

    # Field 'encoding' types
    LITTLE_ENDIAN = "little endian"
    BIG_ENDIAN = "big endian"

    def __init__(self, name, length, format=BINARY, encoding=None, constraints=[]):
        bdec.entry.Entry.__init__(self, name, length, [], constraints)
        assert format in self._formats

        if encoding is None:
            if format == self.TEXT:
                encoding = "ascii"
            else:
                # We default to big endian for non text types, as little
                # endian requires data with a length of a multiple of 8
                encoding = self.BIG_ENDIAN

        self.format = format
        self.encoding = encoding

    def _get_expected(self):
        for constraint in self.constraints:
            if isinstance(constraint, Equals):
                return constraint.limit.evaluate({})
        return None
    expected = property(_get_expected)

    def _convert_type(self, data, expected_type):
        try:
            return expected_type(data)
        except: 
            raise BadFormatError(self, data, expected_type)

    def _encode_data(self, data, length):
        if isinstance(data, dt.Data):
            result = data.copy()
        elif self.format == self.BINARY:
            result = dt.Data.from_binary_text(self._convert_type(data, str))
        elif self.format == self.HEX:
            result = dt.Data.from_hex(self._convert_type(data, str))
        elif self.format == self.TEXT:
            text = self._convert_type(data, str)
            try:
                result = dt.Data(text.encode(self.encoding))
            except UnicodeDecodeError:
                raise BadEncodingError(self, data)
        elif self.format == self.INTEGER:
            
            assert self.encoding in [self.BIG_ENDIAN, self.LITTLE_ENDIAN]
            if self.encoding == self.BIG_ENDIAN:
                result = dt.Data.from_int_big_endian(self._convert_type(data, int), length)
            else:
                result = dt.Data.from_int_little_endian(self._convert_type(data, int), length)
        elif self.format == self.FLOAT:
            assert self.encoding in [self.BIG_ENDIAN, self.LITTLE_ENDIAN]
            if self.encoding == self.BIG_ENDIAN:
                result = dt.Data.from_float_big_endian(self._convert_type(data, float), length)
            else:
                result = dt.Data.from_float_little_endian(self._convert_type(data, float), length)
        else:
            raise Exception("Unknown field format of '%s'!" % self.format)

        return result

    def encode_value(self, value, length=None):
        """
        Convert an object to a dt.Data object.

        Can raise dt.DataError errors.
        """
        if length is None:
            try:
                length = self.length.evaluate({})
            except exp.UndecodedReferenceError:
                # The length isn't available...
                pass

        try:
            return self._encode_data(value, length)
        except dt.DataError, ex:
            raise FieldDataError(self, ex)

    def _get_context(self, query, context):
        try:
            result = query(context, self)
        except bdec.entry.MissingInstanceError:
            if not self.is_hidden():
                raise
            expected = self._get_expected()
            if expected is None:
                raise
            result = self.decode_value(expected)
        return result

    def _fixup_value(self, value):
        expected = self._get_expected()
        if expected is not None and value in [None, '']:
            # We handle strings as a prompt to use the expected value. This is
            # because the named item may be in the output, but not necessarily
            # the value (eg: in the xml representation, it is clearer to not
            # display the expected value).
            value = self.decode_value(expected)
        return value

    def _encode(self, query, value):
        yield self.encode_value(value)

    def __str__(self):
        result = "%s '%s'" % (self.format, self.name)
        if self.format not in [self.HEX, self.BINARY]:
            result += ' (%s)' % self.encoding
        return result

    def _decode_int(self, data):
        if self.encoding == self.LITTLE_ENDIAN:
            result = data.get_little_endian_integer()
        else:
            # If we aren't explicitly little endian, we become big endian.
            # This is because we can sometimes convert a non-integer to
            # an integer (eg: we may want to treat a string character as an
            # integer, to ensure we are in a given character range).
            result = int(data)
        return result

    def decode_value(self, data):
        """
        Get a python instance from a data object.
        """
        if self.format == self.BINARY:
            return data.copy(klass=_BinaryData)
        elif self.format == self.HEX:
            return data.copy(klass=_HexData)
        elif self.format == self.TEXT:
            result = data.text(self.encoding)
        elif self.format == self.INTEGER:
            result = self._decode_int(data)
        elif self.format == self.FLOAT:
            if self.encoding == self.LITTLE_ENDIAN:
                result = data.get_litten_endian_float()
            else:
                result = float(data)
        else:
            raise Exception("Unknown field format of '%s'!" % self.format)
        return result

