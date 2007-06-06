import dcdr.data as dt
import dcdr.entry

class FieldNotDecodedError(dcdr.DecodeError):
    pass

class BadDataError(dcdr.DecodeError):
    def __init__(self, field, expected, actual):
        self.field = field
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return "'%s' expected %s, got %s" % (self.field.name, self.expected.get_binary_text(), self.actual.get_binary_text())

class BadEncodingError(dcdr.DecodeError):
    pass

class BadFormatError(dcdr.DecodeError):
    """
    Got the wrong sort of data type when encoding.
    """
    pass

class InvalidLengthData(dcdr.DecodeError):
    """
    Got given data of the wrong size to encode.
    """
    pass

class Field(dcdr.entry.Entry):

    # Field format types
    TEXT = "text"
    INTEGER = "integer"
    HEX = "hex"
    BINARY = "binary"

    _formats = [TEXT, INTEGER, HEX, BINARY]

    # Field 'encoding' types
    LITTLE_ENDIAN = "little endian"
    BIG_ENDIAN = "big endian"

    def __init__(self, name, length, format=BINARY, encoding=None, expected=None):
        dcdr.entry.Entry.__init__(self, name)
        assert format in self._formats
        assert expected is None or isinstance(expected, dt.Data)

        if encoding is None:
            if format == self.TEXT:
                encoding = "ascii"
            else:
                # We default to big endian for non text types, as little
                # endian requires data with a length of a multiple of 8
                encoding = self.BIG_ENDIAN

        self.length = length
        self._format = format
        self._encoding = encoding
        self.data = None
        self._expected = expected

    def _decode(self, data):
        """ see dcdr.entry.Entry._decode """
        length = int(self.length)
        self.data = data.pop(length)
        if self._expected is not None:
            if int(self._expected) != int(self.data):
                raise BadDataError(self, self._expected, self.data)
        return []

    def _check_type(self, data, expected_type):
        # Try to conver object to the expected type; if it fails, raise
        # an error.
        try:
            expected_type(data)
        except:
            raise BadFormatError(data, expected_type)

    def encode(self, query, context):
        """
        Note that we override 'encode', not '_encode', as we do not want to query
        for items with an expected value.
        """
        if self._expected is not None:
            # We have expected data, so just return that as the encoded data
            yield self._expected
            return

        data = query(context, self.name)
        length = int(self.length)
        if self._format == self.BINARY:
            self._check_type(data, str)
            result = dt.Data.from_binary_text(data)
        elif self._format == self.HEX:
            self._check_type(data, str)
            result = dt.Data.from_hex(data)
        elif self._format == self.TEXT:
            self._check_type(data, str)
            try:
                result = dt.Data(data.encode(self._encoding))
            except UnicodeDecodeError:
                raise BadEncodingError(self, self._encoding, data)
        elif self._format == self.INTEGER:
            self._check_type(data, int)
            assert self._encoding in [self.BIG_ENDIAN, self.LITTLE_ENDIAN]
            if self._encoding == self.BIG_ENDIAN:
                result = dt.Data.from_int_big_endian(data, int(self.length))
            else:
                result = dt.Data.from_int_little_endian(data, int(self.length))
        else:
            raise Exception("Unknown field format of '%s'!" % self._format)

        if len(result) != length:
            raise InvalidLengthData(length, data)
        yield result

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
            try:
                result = unicode(str(self.data), self._encoding)
            except UnicodeDecodeError:
                raise BadEncodingError(self, self._encoding, str(self.data))
        elif self._format == self.INTEGER:
            result = int(self)
        else:
            raise Exception("Unknown field format of '%s'!" % self._format)
        return result
