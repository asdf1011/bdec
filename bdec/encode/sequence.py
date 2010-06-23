
from bdec.encode.entry import EntryEncoder

class SequenceEncoder(EntryEncoder):
    def _encode(self, query, value):
        for child in self.children:
            for data in child.encoder.encode(query, value, 0):
                yield data

