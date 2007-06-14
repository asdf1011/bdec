import bdec.data as dt
import bdec.entry

class FieldError(bdec.DecodeError):
    def __init__(self, field):
        bdec.DecodeError.__init__(self, field)
        assert isinstance(field, Field)
        self.field = field

    def __str__(self):
        return "%s: %s" % (self.__class__, self.field)

class FieldNotDecodedError(FieldError):
    def __init__(self, field):
        FieldError.__init__(self, field)

class BadDataError(FieldError):
    def __init__(self, field, expected, actual):
        FieldError.__init__(self, field)
        assert isinstance(expected, dt.Data)
        assert isinstance(actual, dt.Data)
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return "'%s' expected %s, got %s" % (self.field.name, self.expected.get_binary_text(), self.actual.get_binary_text())

class BadEncodingError(FieldError):
    def __init__(self, field, data):
        FieldError.__init__(self, field)
        self.data = data

    def __str__(self):
        return "BadEncodingError: %s couldn't encode %s" % (self.field, self.data)

class BadFormatError(FieldError):
    """
    Got the wrong sort of data type when encoding.
    """
    def __init__(self, field, data, expected_type):
        FieldError.__init__(self, field)
        self.data = data
        self.expected_type = expected_type

    def __str__(self):
        return "BadFormatError: %s expected %s got %s" % (self.field, self.expected_type, self.data)

class InvalidLengthData(FieldError):
    """
    Got given data of the wrong size to encode.
    """
    def __init__(self, field, length, data):
        FieldError.__init__(self, field)
        self.length = length
        self.data = data

    def __str__(self):
        return "%s expected length %i, got length %i (%s)" % (self.field, self.length, len(self.data), self.data.get_binary_text())

class FieldDataError(FieldError):
    """
    An error with converting the data to the specified type.
    """
    def __init__(self, field, error):
        FieldError.__init__(self, field)
        self.error = error

    def __str__(self):
        return "%s - %s" % (self.field, self.error)

class Field(bdec.entry.Entry):

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
        bdec.entry.Entry.__init__(self, name)
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
        self._listeners = []

    def add_listener(self, listener):
        """
        Add a listener to be called when the field decodes.
        """
        self._listeners.append(listener)

    def _decode(self, data):
        """ see bdec.entry.Entry._decode """
        length = int(self.length)
        try:
            self.data = data.pop(length)
        except dt.DataError, ex:
            raise FieldDataError(self, ex)

        if self._expected is not None:
            if int(self._expected) != int(self.data):
                raise BadDataError(self, self._expected, self.data)

        for listener in self._listeners:
            listener(self)
        return []

    def _convert_type(self, data, expected_type):
        try:
            return expected_type(data)
        except: 
            raise BadFormatError(self, data, expected_type)

    def _encode_data(self, data):
        """
        Convert an object to a dt.Data object.

        Can raise dt.DataError errors.
        """
        length = int(self.length)
        if self._format == self.BINARY:
            result = dt.Data.from_binary_text(self._convert_type(data, str))
        elif self._format == self.HEX:
            result = dt.Data.from_hex(self._convert_type(data, str))
        elif self._format == self.TEXT:
            text = self._convert_type(data, str)
            try:
                result = dt.Data(text.encode(self._encoding))
            except UnicodeDecodeError:
                raise BadEncodingError(self, data)
        elif self._format == self.INTEGER:
            
            assert self._encoding in [self.BIG_ENDIAN, self.LITTLE_ENDIAN]
            if self._encoding == self.BIG_ENDIAN:
                result = dt.Data.from_int_big_endian(self._convert_type(data, int), length)
            else:
                result = dt.Data.from_int_little_endian(self._convert_type(data, int), length)
        else:
            raise Exception("Unknown field format of '%s'!" % self._format)

        if len(result) != length:
            raise InvalidLengthData(self, length, result)
        if self._expected is not None and result != self._expected:
            raise BadDataError(self, self._expected, result)
        return result

    def encode(self, query, context):
        """
        Note that we override 'encode', not '_encode', as we do not want to query
        for items with an expected value.
        """
        if self._expected is not None:
            if self.is_hidden():
                try:
                    data = query(context, self)
                except bdec.entry.MissingInstanceError:
                    # The hidden variable wasn't included in the output, so just
                    # use the 'expected' value.
                    yield self._expected
                    return
            else:
                # We are an expected value, but not hidden (and so must be present
                # in the data to be encoded).
                data = query(context, self)
                
            if data is None or data == "":
                # The expected value object was present, but didn't have any data (eg:
                # the xml output may not include expected values).
                yield self._expected
                return
        else:
            # We don't have any expected data, so we'll query it from the input.
            try:
                data = query(context, self)
            except bdec.entry.MissingInstanceError:
                if not self.is_hidden():
                    # The field wasn't hidden, but we failed to query the data.
                    raise
                data = context

        try:
            result = self._encode_data(data)
        except dt.DataError, ex:
            raise FieldDataError(self, ex)
        yield result

    def __str__(self):
        return "%s '%s' (%s)" % (self._format, self.name, self._encoding)

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
                raise BadEncodingError(self, str(self.data))
        elif self._format == self.INTEGER:
            result = int(self)
        else:
            raise Exception("Unknown field format of '%s'!" % self._format)
        return result
