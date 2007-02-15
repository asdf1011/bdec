import dcdr.entry

class FieldNotDecodedError(dcdr.DecodeError):
    pass

class BadDataError(dcdr.DecodeError):
    def __init__(self, field, expected, actual):
        self.field = field
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return "Expected %s, got %s" % (self.expected.get_hex(), self.actual.get_hex())

class Field(dcdr.entry.Entry):

    # Field format types
    TEXT = "text"
    INTEGER = "integer"
    HEX = "hex"
    BINARY = "binary"

    # Field 'encoding' types
    LITTLE_ENDIAN = "little endian"
    BIG_ENDIAN = "big endian"

    def __init__(self, name, get_length, format=BINARY, encoding=None, expected=None):
        dcdr.entry.Entry.__init__(self, name)

        if encoding is None:
            if format == self.TEXT:
                encoding = "ascii"
            else:
                # We default to big endian for non text types, as little
                # endian requires data with a length of a multiple of 8
                encoding = self.BIG_ENDIAN

        self._get_length = get_length
        self._format = format
        self._encoding = encoding
        self.data = None
        self._expected = expected

    def _decode(self, data):
        """ see dcdr.entry.Entry._decode """
        length = self._get_length()
        self.data = data.pop(length)
        if self._expected is not None:
            if self._expected != self.data:
                raise BadDataError(self, self._expected, self.data)
        return []

    def __int__(self):
        assert self._encoding in [self.BIG_ENDIAN, self.LITTLE_ENDIAN]
        if self._encoding == self.BIG_ENDIAN:
            result = int(self.data)
        else:
            result = self.data.get_little_endian_integer()
        return result

    def get_value(self):
        """ Get the decoded value """
        if self.data is None:
            raise FieldNotDecodedError(self)

        if self._format == self.BINARY:
            result = self.data.get_binary_text()
        elif self._format == self.HEX:
            result = self.data.get_hex()
        elif self._format == self.TEXT:
            result = str(self.data).decode(self._encoding)
        elif self._format == self.INTEGER:
            result = int(self)
        else:
            raise Exception("Unknown field format of '%s'!" % self._format)
        return result
