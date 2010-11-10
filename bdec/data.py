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

import itertools
import os
import string
import struct
import weakref

import bdec

class DataError(Exception):
    """Base class for all data errors."""
    def __str__(self):
        return 'Data error!'
    def __unicode__(self):
        return str(self)

class DataLengthError(DataError):
    pass

class NotEnoughDataError(DataLengthError):
    """Not enough data was available to fulfill the request."""
    def __init__(self, requested_length, available_length):
        self.requested = requested_length
        self.available = available_length

    def __str__(self):
        return "Asked for %i bits, but only have %i bits available!" % (self.requested, self.available)


class PoppedNegativeBitsError(DataError):
    """A negative amount of data was requested."""
    def __init__(self, requested_length):
        self.requested = requested_length
        assert self.requested < 0

    def __str__(self):
        return "Data source asked for %i bits!" % self.requested

class IntegerTooLongError(DataLengthError):
    """A data object was too long to be converted to an integer."""
    def __init__(self, value, length):
        self.value = value
        self.length = length

    def __str__(self):
        return "Cannot encode value %i in %i bits" % (self.value, self.length)

class HexNeedsFourBitsError(DataLengthError):
    """Raised when attempting to convert data to hex, and we don't
        have a multiple of 4 bits. """
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return 'Conversion to hex needs a multiple of 4 bits; data has %i bits' % len(self.data)

class ConversionNeedsBytesError(DataLengthError):
    """An operation that needed whole bytes had a data buffer with bits."""
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return 'Conversion needs data to be whole bytes; data has %i bits' % len(self.data)

class FloatLengthError(DataLengthError):
    """Invalid size for decoding a float."""
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return 'Cannot decode a float of %i bits; must be 4 or 8 bytes.' % len(self.data)

class InvalidBinaryTextError(DataError):
    """A binary text to data conversion failed."""
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return "Invalid binary text '%s'" % self.text

class InvalidHexTextError(DataError):
    """A hex text to data conversion failed."""
    def __init__(self, hex):
        self.hex = hex

    def __str__(self):
        return "Invalid hext text: '%s'" % self.hex

class BadTextEncodingError(DataError):
    """A data object was unable to be encoded in the specified text encoding."""
    def __init__(self, data, encoding):
        self.data = data
        self.encoding = encoding

    def __str__(self):
        return "'%s' can't convert '%s'" % (self.encoding, self.data)

class _OutOfDataError(Exception):
    """Not derived from DataError as this is an internal error."""

# Note that we don't include 'x' in the hex characters...
_HEX_CHARACTERS = ['a', 'b', 'c', 'd', 'e', 'f', 'A', 'B', 'C', 'D', 'E', 'F', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

class _ByteBuffer(object):
    def read_byte(self, offset):
        raise NotImplementedError()

    def __len__(self):
        raise NotImplementedError()

    def _byte_iter(self):
        for i in range(len(self)):
            yield self.read_byte(i)

    def _bytes(self):
        return ''.join(chr(c) for c in self._byte_iter())

    def __add__(self, other):
        return _MemoryBuffer(self._bytes() + other._bytes())

    def _shift_chars(self, num_bits):
        byte = 0
        for char in self._bytes():
            value = byte << (8 - num_bits)
            byte = ord(char)
            value |= byte >> num_bits
            yield chr(value & 0xFF)
        yield chr((byte << (8 - num_bits)) & 0xff)

    def __rshift__(self, num_bits):
        if num_bits == 0:
            return self
        elif num_bits % 8  == 0:
            return _MemoryBuffer('\x00' * (num_bits / 8) + self._bytes())
        return _MemoryBuffer(''.join(self._shift_chars(num_bits)))

    def __getslice__(self, start, end):
        result = _MemoryBuffer(self._bytes()[start:end])
        return result


class _FileBuffer(_ByteBuffer):
    """Byte buffer that reads from a seekable file."""
    def __init__(self, file):
        self._file = file
        self._offset = None

    def read_byte(self, offset):
        if offset != self._offset:
            self._file.seek(offset)
        result = self._file.read(1)
        if len(result) == 0:
            raise _OutOfDataError()
        self._offset = offset + 1
        return ord(result)

    def __len__(self):
        pos = self._file.tell()
        self._file.seek(0, os.SEEK_END)
        result = self._file.tell()
        self._file.seek(pos)
        return result


class _NonSeekingFileBuffer(_ByteBuffer):
    """Byte buffer that reads from a non-seekable file.

    NOTE: Will keep the file in memory as it is read in to support streaming."""
    def __init__(self, file):
        self._file = file
        self._buffer = ''

    def read_byte(self, offset):
        extra_bytes_needed = offset + 1 - len(self._buffer)
        if extra_bytes_needed > 0:
            self._buffer += self._file.read(extra_bytes_needed)
            if len(self._buffer) < offset + 1:
                raise _OutOfDataError()
        return ord(self._buffer[offset])

    def __len__(self):
        try:
            for offset in itertools.count():
                self.read_byte(offset)
        except _OutOfDataError:
            return offset


class _MemoryBuffer(_ByteBuffer):
    """Byte buffer that reads directly from in memory data."""
    def __init__(self, buffer):
        assert isinstance(buffer, str), "Expected a string; got %s!" % repr(buffer)
        self._buffer = buffer

    def read_byte(self, offset):
        """Read a byte at a given offset"""
        if offset >= len(self._buffer):
            raise _OutOfDataError()
        return ord(self._buffer[offset])

    def __len__(self):
        return len(self._buffer)

    def _bytes(self):
        return self._buffer


class Data(object):
    """
    A class to hold information about data to be decoded.
    
    The data is not actually validated to be available until it is used, at
    which stage NotEnoughDataError can be thrown.
    """
    def __init__(self, buffer="", start=None, end=None):
        """Construct a data object.

        buffer - Can be either a string or a file instance.
        start - The bit the data starts at in the buffer. Bit 0 is the most
           significant bit in the first byte. If None, the data starts at
           bit zero.
        end - The bit the data ends at. If None, the data ends at the end of
           the buffer.
        """

        # Note: We can detect the length of string and empty buffers at
        # initialisation time; it is a speed win to do so. However, that means
        # data objects behave differently depending on what they were 
        # constructed from (a source of bugs) (eg: verification of length
        # at pop time, as opposed to read time).
        if isinstance(buffer, str):
            self._buffer = _MemoryBuffer(buffer)
        elif isinstance(buffer, _ByteBuffer):
            self._buffer = buffer
        elif hasattr(buffer, 'seek'):
            # Treat the buffer as a file object.
            try:
                buffer.tell()
                self._buffer = _FileBuffer(buffer)
            except IOError:
                # This file doesn't appear to support seeking
                self._buffer = _NonSeekingFileBuffer(buffer)
        else:
            raise Exception("Unknown data source '%s'" % type(buffer)) 

        if start is None:
            start = 0

        assert end is None or start <= end
        self._start = start
        self._end = end

    def pop(self, length):
        """Return a data instance for representing the start of this data.

        The popped data will no longer be available from this instance. If not
        enough data is available, an error can either be raised now, or later
        when the popped data is used.

        length -- The length in bits to remove.
        """
        if length < 0:
            raise PoppedNegativeBitsError(length)
        if self._end is not None and length > self._end - self._start:
            raise NotEnoughDataError(length, self._end - self._start)

        result = Data(self._buffer, self._start, self._start + length)
        self._start += length
        return result

    def copy(self, klass=None):
        """Create a copy of this data instance.

        klass - The data class to use when creating the copy. If None, will
            use Data.
        """
        if not klass:
            klass = Data
        return klass(self._buffer, self._start, self._end)

    def bytes(self):
        """Return a str instance representing the bytes held by this data.

        If the data length isn't a multiple of 8 bits, a DataError will be
        raised."""
        return "".join(chr(byte) for byte in self._get_bytes())

    def text(self, encoding):
        """Return a unicode object that represents the data buffer.

        If the data length isn't a multiple of 8 bits, a DataError will be
        raised. If the data cannot be converted to the given encoding, a
        BadTextEncodingError error will be raised.
        
        encoding -- The unicode encoding the data is in. """
        try:
            return unicode(self.bytes(), encoding)
        except UnicodeDecodeError:
            raise BadTextEncodingError(self, encoding)

    def __repr__(self):
        """Return a textual representation of the data."""
        if len(self) % 8 == 0:
            return 'hex (%i bytes): %s' % (len(self) / 8, self.get_hex())
        else:
            return 'bin (%i bits): %s' % (len(self), self.get_binary_text())

    def _get_bits(self):
        """
        Get an iterator to the bits contained in this buffer.

        Can throw NotEnoughDataError if the backing store doesn't have the
        required amount of data for this instance.
        """
        i = 0
        while self._end is None or i < self._end - self._start:
            try:
                yield self._get_bit(i)
            except _OutOfDataError:
                if self._end is not None:
                    raise NotEnoughDataError(self._end - self._start, i)
                break
            i += 1

    def __eq__(self, other):
        if not isinstance(other, Data):
            return NotImplemented

        # TODO: This bit by bit comparison is slow...
        a = self._get_bits()
        b = other._get_bits()
        while 1:
            try:
                a_bit = a.next()
            except StopIteration:
                try:
                    b.next()
                    # Not equal, as 'other' is longer then we are
                    return False
                except StopIteration:
                    # Equal, as same size, same values
                    return True

            try:
                b_bit = b.next()
            except StopIteration:
                # Not equal, as we are longer than 'other'
                return False

            if a_bit != b_bit:
                return False

    def __ne__(self, other):
        if not isinstance(other, Data):
            return NotImplemented

        return not self == other

    def __len__(self):
        if self._end is None:
            end = len(self._buffer) * 8
            if end < self._start:
                raise NotEnoughDataError(0, end - self._start)
            self._end = end
        return self._end - self._start

    def __nonzero__(self):
        return not self.empty()

    def empty(self):
        """Check to see if we have data left.

        If the length of the data is known, that value will be used. If the
        length is unknown, it will see if we can read more data.
        """
        if self._end is not None:
            return self._end == self._start

        # We don't know where the data ends, so look to see if we can read
        # more of the data.
        try:
            self._get_bits().next()
            return False
        except StopIteration:
            pass
        return True

    def _get_bit(self, i):
        """
        Query the backend byte source for a given bit.

        If the backend doesn't have the data available, or we are querying
        outside of our bounds, an _OutOfDataError is raised.
        """
        i += self._start
        if self._end is not None and i >= self._end:
            raise _OutOfDataError()
        byte = i / 8
        i = i % 8
        return (self._buffer.read_byte(byte) >> (7 - i)) & 1

    def validate(self):
        """Validate that the data is available in the backing store.

        Will cause the all the data represented by this instance to be loaded
        into memory. If this data instance doesn't have a lenght, will return
        without failing.

        Will throw NotEnoughDataError if the data isn't available.
        """
        if not self._end:
            return
        length = len(self)
        if length == 0:
            return

        try:
            # We don't want to ask for the length of the backing store
            # initially, as that may cause it to be loaded into memory (ie:
            # if it's a stream that doesn't support streaming). So we instead
            # just attempt to read the last bit we want...
            self._get_bit(length-1)
        except _OutOfDataError:
            # We don't have enough data for reading this byte... determine how
            # much data we really do have.
            num_bytes = len(self._buffer)
            available_bits = num_bytes * 8 - self._start
            raise NotEnoughDataError(length, available_bits)
        
    def __int__(self):
        """
        Convert the buffer to an integer

        Conversion is big endian.
        """
        if not len(self):
            return 0

        data = self.copy()
        result = 0
        for bit in data.pop(len(data) % 8)._get_bits():
            result = (result << 1) | bit
        for byte in data._get_bytes():
            result = (result << 8) | byte
        return result

    def __add__(self, other):
        if not isinstance(other, Data):
            raise NotImplementedError()

        if not self._end:
            self._end = self._start + len(self)
        if not other._end:
            other._end = other._start + len(other)
        self.validate()
        other.validate()

        # Check for early outs
        if not self:
            return other
        if not other:
            return self

        left = self._buffer[self._start / 8:(self._end - 1) / 8 + 1]
        right = other._buffer[other._start / 8:(other._end - 1) / 8 + 1]

        # Shift the shorter data object (as the shift is relatively intensive)
        if len(self) < len(other):
            # The left hand buffer is shorter than the right, so shift it so it
            # aligns with the right
            distance = (other._start - self._end) % 8
            left_start = self._start % 8 + distance
            left >>= distance

            # It's possible we have to truncate the buffer here, as we may
            # have create an extra byte on the right that contains data we
            # don't care about.
            left = left[:(left_start + len(self) - 1) / 8 + 1]
        else:
            # The right hand buffer is shorter than the left, so shift it so it
            # aligns with the left
            distance = (self._end - other._start) % 8
            left_start = (self._start + distance) % 8
            left_start = self._start % 8
            right >>= distance
            right_start = other._start % 8 + distance
            right = right[right_start / 8:(right_start + len(other) - 1) / 8 + 1]

        if (left_start + len(self)) % 8 and len(self) and len(other):
            # The left doesn't end on a whole byte; create a joining byte to
            # connect the left & right
            merge_byte = (left_start + len(self) - 1) / 8

            overlapping_bits = (left_start + len(self)) % 8
            overlap =  left.read_byte(merge_byte) & (0xff << (8 - overlapping_bits))
            overlap |= right.read_byte(0) & (0xff >> overlapping_bits)

            left = left[:merge_byte] + _MemoryBuffer(chr(overlap))
            right = right[1:]

        return Data(left + right, left_start, left_start + len(self) + len(other))

    def _get_bytes(self):
        """
        Return an iterator to a series of byte values in the data.
        """
        if self._start % 8 == 0 and self._end is not None and self._end % 8 == 0:
            # Optimise for the case where we know the length of the data, and
            # it is byte aligned.
            for i in xrange(self._start / 8, self._end / 8):
                try:
                    yield self._buffer.read_byte(i)
                except _OutOfDataError:
                    raise NotEnoughDataError(self._end - self._start, i * 8 - self._start)
        else:
            # Read as many of the bits as possible, yielding the results.
            value = 0
            i = None
            for i, bit in enumerate(self._get_bits()):
                value = (value << 1) | bit
                if (i + 1) % 8 == 0:
                    # We have a new byte!
                    yield value
                    value = 0
            if i is not None and i % 8 != 7:
                raise ConversionNeedsBytesError(self)

    def __float__(self):
        """
        Convert the data buffer to a float that has been encoded in big endian.
        """
        if len(self) == 4 * 8:
            return struct.unpack('>f', self.bytes())[0]
        elif len(self) == 8 * 8:
            return struct.unpack('>d', self.bytes())[0]
        else:
            raise FloatLengthError(self)

    def get_litten_endian_float(self):
        """
        Convert the data buffer to a float that has been encoded in little endian.
        """
        if len(self) == 4 * 8:
            return struct.unpack('<f', self.bytes())[0]
        elif len(self) == 8 * 8:
            return struct.unpack('<d', self.bytes())[0]
        else:
            raise FloatLengthError(self)

    @staticmethod
    def from_float_little_endian(value, length):
        if length == 4 * 8:
            return Data(struct.pack('<f', value))
        elif length == 8 * 8:
            return Data(struct.pack('<d', value))
        else:
            raise FloatLengthError(self)

    @staticmethod
    def from_float_big_endian(value, length):
        if length == 4 * 8:
            return Data(struct.pack('>f', value))
        elif length == 8 * 8:
            return Data(struct.pack('>d', value))
        else:
            raise FloatLengthError(self)

    def get_little_endian_integer(self):
        """
        Get an integer that has been encoded in little endian format
        """
        result = 0
        for byte, value in enumerate(self._get_bytes()):
            result = result | (value << (8 * byte))
        return result

    def get_binary_text(self):
        """
        Get a string representing the binary data.

        eg: 001 10100000
        """
        bits = list(self._get_bits())
        bytes = []
        if len(bits) % 8 != 0:
            bytes.append(bits[0:len(bits) % 8])
        for i in range(len(bits) % 8, len(bits), 8):
            bytes.append(bits[i:i+8])

        bytes = ("".join(str(bit) for bit in byte) for byte in bytes)
        return " ".join(byte for byte in bytes)

    def get_hex(self):
        """
        Get a string representing the data in hex format.
        """
        data = self.copy()
        size = len(data)
        if size % 4 != 0:
            raise HexNeedsFourBitsError(self)

        result = ""
        if size % 8:
            result += "%x" % int(data.pop(4))

        for num in data._get_bytes():
            result += '%02x' % num

        return result

    @staticmethod
    def from_int_little_endian(value, length):
        """Create a data object from an integer.
        
        length -- The length in bits of the data buffer to create."""
        data = int(value)
        if length % 8 != 0:
            raise ConversionNeedsBytesError(self)
        chars = []
        for i in range(length / 8):
            chars.append(chr(data & 0xff))
            data >>= 8
        if data != 0:
            raise IntegerTooLongError(value, length)
        return Data("".join(chars))

    @staticmethod
    def from_int_big_endian(value, length):
        """Create a data object from an integer.
        
        length -- The length in bits of the data buffer to create."""
        data = int(value)
        chars = []
        num_bytes = length / 8
        if length % 8 != 0:
            num_bytes += 1
        for i in range(num_bytes):
            chars.append(chr(data & 0xff))
            data >>= 8
        if data != 0:
            raise IntegerTooLongError(value, length)
        chars.reverse()

        result = Data("".join(chars))
        num_leading_bits = num_bytes * 8 - length
        if num_leading_bits and 0 != int(result.pop(num_leading_bits)):
            # We have an integer that isn't a multiple of 8 bits, and we
            # couldn't quite fit it in the space available.
            raise IntegerTooLongError(value, length)
        return result

    @staticmethod
    def from_hex(hex): 
        """
        Convert a hex string to a data buffer.

        The hex entries can be seperated by whitespace, with multi-byte entries
        seperated on even characters.  For example, '0e 9a bc', or '0e9abc'.

        Entries without whitespace with an odd number of characters will be 
        treated as if it had a leading zero; eg: 'e02' will be interpreted as
        being the two byte value '0e02'.
        """
        buffer = []
        entries = hex.split()
        for entry in entries:
            if len(entry) % 2:
                entry = '0' + entry

            for i in range(len(entry) / 2):
                offset = i * 2
                value = entry[offset:offset + 2]
                for char in value:
                    if char not in _HEX_CHARACTERS:
                        raise InvalidHexTextError(hex)
                buffer.append(int(value, 16))
        return Data("".join(chr(value) for value in buffer))

    @staticmethod
    def from_binary_text(text):
        """
        Create a data object from binary text.

        eg: "001 10100000"
        """
        buffer = []
        value = 0
        length = 0
        for char in text:
            if char not in string.whitespace:
                if char not in ['0', '1']:
                    raise InvalidBinaryTextError(text)
                value <<= 1
                value |= int(char)
                length += 1

                if length == 8:
                    buffer.append(chr(value))
                    length = 0
                    value = 0
        buffer.append(chr(value << (8 - length)))
        return Data("".join(buffer), 0, len(buffer) * 8 - (8 - length))


