import dcdr

class NotEnoughDataError(dcdr.DecodeError):
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

    def pop(self, length):
        """
        Pop data from this data object
        """
        if length > self._end - self._start:
            raise NotEnoughDataError("Asked for %i bits, but only have %i bits available!" % (length, self._end - self._start))

        result = Data(self._buffer, self._start, self._start + length)
        self._start += length
        return result

    def __str__(self):
        assert self._start % 8 == 0
        assert self._end % 8 == 0
        return self._buffer[self._start / 8:self._end / 8]

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

    @staticmethod
    def from_hex(hex): 
        hex = hex.upper()
        assert hex[:2] == "0X"
        hex = hex[2:]
        if len(hex) % 2:
            hex = '0' + hex

        buffer = []
        for i in range(len(hex) / 2):
            offset = i * 2
            value = hex[offset:offset + 2]
            buffer.append(int(value, 16))
        return Data("".join(chr(value) for value in buffer))
