import dcdr.entry

class FieldNotDecodedError(dcdr.DecodeError):
    pass

class Field(dcdr.entry.Entry):
    TEXT = "text"
    INTEGER = "integer"
    HEXSTRING = "hexstring"
    BINARY = "binary"

    def __init__(self, name, get_length, format=BINARY, encoding=""):
        dcdr.entry.Entry.__init__(self, name)

        self._get_length = get_length
        self._format = format
        self._encoding = encoding
        self.data = None

    def _decode(self, data):
        """ see dcdr.entry.Entry._decode """
        length = self._get_length()
        self.data = data.pop(length)
        return []

    def get_value(self):
        """ Get the decoded value """
        if self.data is None:
            raise FieldNotDecodedError(self)

        if self._format == self.BINARY:
            return self.data.get_binary_text()
        raise Exception("Unknown field format of '%s'!" % self._format)
