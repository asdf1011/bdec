
from bdec.encode.entry import EntryEncoder

class FieldEncoder(EntryEncoder):
    def _encode(self, query, value):
        yield self.entry.encode_value(value)

    def _fixup_value(self, value):
        expected = self.entry.expected
        if expected is not None and value in [None, '']:
            # We handle strings as a prompt to use the expected value. This is
            # because the named item may be in the output, but not necessarily
            # the value (eg: in the xml representation, it is clearer to not
            # display the expected value).
            value = self.entry.decode_value(expected)
        return value
