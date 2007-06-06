import dcdr
import string

class NotEnoughDataError(dcdr.DecodeError):
    pass

class HexNeedsFourBitsError(dcdr.DecodeError):
    """ Raised when attempting to convert data to hex, and we don't
        have a multiple of 4 bits. """
    pass

class ConversionNeedsBytesError(dcdr.DecodeError):
    pass

class InvalidBinaryTextError(dcdr.DecodeError):
    pass

class InvalidHexTextError(dcdr.DecodeError):
    pass

class Data:
    """ A class to hold data to be decoded """
    def __init__(self, buffer, start=None, end=None):
        self._buffer = buffer
        if start is None:
            start = 0
        if end is None:
            end = len(self._buffer) * 8

        self._start = start
        self._end = end
        assert isinstance(self._start, int)
        assert isinstance(self._end, int)

    def pop(self, length):
        """
        Pop data from this data object
        """
        if length > self._end - self._start:
            raise NotEnoughDataError("Asked for %i bits, but only have %i bits available!" % (length, self._end - self._start))

        result = Data(self._buffer, self._start, self._start + length)
        self._start += length
        return result

    def copy(self):
        return Data(self._buffer, self._start, self._end)

    def __str__(self):
        return "".join(chr(byte) for byte in self._get_bytes())

    def __eq__(self, other):
        if not isinstance(other, Data):
            return NotImplemented

        if (self._end - self._start) != (other._end - other._start):
            return False

        for i in range(self._end - self._start):
            if self._get_bit(i + self._start) != other._get_bit(i + other._start):
                return False
        return True

    def __ne__(self, other):
        if not isinstance(other, Data):
            return NotImplemented

        return not self == other

    def __len__(self):
        return self._end - self._start

    def _get_bit(self, i):
        byte = i / 8
        i = i % 8
        return (ord(self._buffer[byte]) >> (7 - i)) & 1
        
    def __int__(self):
        """
        Convert the buffer to an integer

        Conversion is big endian.
        """
        result = 0
        for bit in range(self._start, self._end):
            result = (result << 1) | self._get_bit(bit)
        return result

    def __add__(self, other):
        if not isinstance(other, Data):
            return NotImplemented
        # Incredibly inefficient...
        return Data.from_binary_text(self.get_binary_text() + other.get_binary_text())

    def _get_bytes(self):
        """
        Return an iterator to a series of byte values in the data.
        """
        if (self._end - self._start) % 8 != 0:
            raise ConversionNeedsBytesError(self)
        if self._start % 8 == 0:
            # We don't need to do this on a bit by bit, as we
            # are reading aligned bytes...
            for byte in xrange(self._start / 8, self._end / 8):
                yield ord(self._buffer[byte])
        else:
            # We have to read bit by bit
            for i in xrange(self._start, self._end, 8):
                value = 0
                for bit in xrange(8):
                    value = (value << 1) | self._get_bit(i + bit)
                yield value

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
        bits = [self._get_bit(bit) for bit in range(self._start, self._end)]
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
        bits = [self._get_bit(bit) for bit in range(self._start, self._end)]
        if len(bits) % 4 != 0:
            raise HexNeedsFourBitsError(self)

        chars = []
        for i in range(0, len(bits), 4):
            value = 0
            for bit in range(4):
                value |= bits[i + bit] << (3-bit)
            chars.append(hex(value)[2:])
        return "".join(chars)

    @staticmethod
    def from_int_little_endian(value, length):
        data = int(value)
        if length % 8 != 0:
            raise ConversionNeedsBytesError()
        chars = []
        for i in range(length / 8):
            chars.append(chr(data & 0xff))
            data >>= 8
        if data != 0:
            raise NotEnoughDataError(value)
        return Data("".join(chars))

    @staticmethod
    def from_int_big_endian(value, length):
        data = int(value)
        chars = []
        num_bytes = length / 8
        if length % 8 != 0:
            num_bytes += 1
        for i in range(num_bytes):
            chars.append(chr(data & 0xff))
            data >>= 8
        if data != 0:
            raise NotEnoughDataError(value, length)
        chars.reverse()

        result = Data("".join(chars))
        if 0 != int(result.pop(num_bytes * 8 - length)):
            # We have an integer that isn't a multiple of 8 bits, and we
            # couldn't quite fit it in the space available.
            raise NotEnoughDataError(value, length)
        return result

    @staticmethod
    def from_hex(hex): 
        """
        Convert a hex string to a data buffer
        """
        if len(hex) % 2:
            hex = '0' + hex

        buffer = []
        for i in range(len(hex) / 2):
            offset = i * 2
            value = hex[offset:offset + 2]
            try:
                buffer.append(int(value, 16))
            except ValueError:
                raise InvalidHexTextError(hex)
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
                    raise InvalidBinaryTextError("Invalid binary text!", text)
                value <<= 1
                value |= int(char)
                length += 1

                if length == 8:
                    buffer.append(chr(value))
                    length = 0
                    value = 0
        buffer.append(chr(value << (8 - length)))
        return Data("".join(buffer), 0, len(buffer) * 8 - (8 - length))
