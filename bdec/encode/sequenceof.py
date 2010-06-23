
from bdec import DecodeError
from bdec.encode.entry import EntryEncoder

class InvalidSequenceOfCount(DecodeError):
    """Raised during encoding when an invalid length is found."""
    def __init__(self, seq, expected, actual):
        DecodeError.__init__(self, seq)
        self.sequenceof = seq
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return "%s expected count of %i, got %i" % (self.sequenceof, self.expected, self.actual)

class SequenceOfEncoder(EntryEncoder):
    def _encode(self, query, value):
        count = 0
        for i, child in enumerate(value):
            count += 1
            for data in self.children[0].encoder.encode(query, value, i):
                yield data

        if self.entry.count is not None and self.entry.count.evaluate({}) != count:
            raise InvalidSequenceOfCount(self.entry, self.entry.count.evaluate({}), count)
