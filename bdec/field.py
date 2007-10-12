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
        expected = self.field.decode_value(self.expected)
        try:
            actual = self.field.decode_value(self.actual)
        except bdec.DecodeError:
            # We couldn't convert the object to the expected format,
            # so we'll display it as binary.
            actual = self.actual.get_binary_text()
        return "'%s' expected %s, got %s" % (self.field.name, repr(expected), repr(actual))

class BadRangeError(FieldError):
    def __init__(self, field, actual):
        FieldError.__init__(self, field)
        self.actual = actual

    def _range(self):
        if self.field.min is not None:
            result = "[%i, " % int(self.field.min)
        else:
            result = "(-inf, "
        if self.field.max is not None:
            result += "%i]" % int(self.field.max)
        else:
            result = "inf)"
        return result

    def __str__(self):
        return "'%s' value %s not in range %s" % (self.field.name, self.actual, self._range())

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
        return "BadFormatError: %s expected %s got '%s'" % (self.field, self.expected_type, self.data)


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

    def __init__(self, name, length, format=BINARY, encoding=None, expected=None, min=None, max=None):
        bdec.entry.Entry.__init__(self, name, length, [])
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
        self.data = None
        self.expected = expected
        self.min = min
        self.max = max

    def _set_expected(self, expected):
        assert expected is None or isinstance(expected, dt.Data)
        if expected is not None and self.length is not None:
            import bdec.spec.xmlspec
            try:
                length = int(self.length)
                if length != len(expected):
                    raise FieldDataError(self, 'Expected data should have a length of %i, got %i' % (length, len(expected)))
            except bdec.spec.xmlspec.UndecodedReferenceError:
                pass
        self._expected = expected
    expected = property(lambda self: self._expected, _set_expected)

    def _decode(self, data, child_context):
        """ see bdec.entry.Entry._decode """
        yield (True, self, data)

        self.data = data.pop(int(self.length))
        if self.expected is not None:
            if int(self.expected) != int(self.data):
                raise BadDataError(self, self.expected, self.data)
        self._validate_range(self.data)

        yield (False, self, self.data)

    def _convert_type(self, data, expected_type):
        try:
            return expected_type(data)
        except: 
            raise BadFormatError(self, data, expected_type)

    def _encode_data(self, data):
        length = int(self.length)
        if self.format == self.BINARY:
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
        else:
            raise Exception("Unknown field format of '%s'!" % self.format)

        return result

    def encode_value(self, value):
        """
        Convert an object to a dt.Data object.

        Can raise dt.DataError errors.
        """
        try:
            return self._encode_data(value)
        except dt.DataError, ex:
            raise FieldDataError(self, ex)

    def _encode(self, query, context):
        """
        Note that we override 'encode', not '_encode', as we do not want to query
        for items with an expected value.
        """
        if self.expected is not None:
            if self.is_hidden():
                try:
                    data = query(context, self)
                except bdec.entry.MissingInstanceError:
                    # The hidden variable wasn't included in the output, so just
                    # use the 'expected' value.
                    yield self.expected
                    return
            else:
                # We are an expected value, but not hidden (and so must be present
                # in the data to be encoded).
                data = query(context, self)
                
            if data is None or data == "":
                # The expected value object was present, but didn't have any data (eg:
                # the xml output may not include expected values).
                yield self.expected
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

        self._validate_range(data)

        result = self.encode_value(data)
        if self.expected is not None and result != self.expected:
            raise BadDataError(self, self.expected, result)
        yield result

    def __str__(self):
        return "%s '%s' (%s)" % (self.format, self.name, self.encoding)

    def _validate_range(self, data):
        """
        Validate any range constraints that may have been placed on this field.
        """
        if self.min is not None or self.max is not None:
            value = self._decode_int(data)
            if self.min is not None:
                if value < int(self.min):
                    raise BadRangeError(self, value)
            if self.max is not None:
                if value > int(self.max):
                    raise BadRangeError(self, value)

    def __int__(self):
        return self._decode_int(self.data)

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

    def get_value(self):
        """ Get the decoded value """
        if self.data is None:
            raise FieldNotDecodedError(self)
        return self.decode_value(self.data)

    def decode_value(self, data):
        """
        Get a python instance from a data object.
        """
        if self.format == self.BINARY:
            result = data.get_binary_text()
        elif self.format == self.HEX:
            result = data.get_hex()
        elif self.format == self.TEXT:
            try:
                result = unicode(str(data), self.encoding)
            except UnicodeDecodeError:
                raise BadEncodingError(self, str(data))
        elif self.format == self.INTEGER:
            result = self._decode_int(data)
        else:
            raise Exception("Unknown field format of '%s'!" % self.format)
        return result

    def range(self):
        import bdec.spec.xmlspec
        try:
            min = max = int(self.length)
        except bdec.spec.xmlspec.UndecodedReferenceError:
            min = 0
            max = bdec.entry.Range.MAX
        return bdec.entry.Range(min, max)
