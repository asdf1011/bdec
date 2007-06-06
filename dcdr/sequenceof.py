import dcdr.entry

class SequenceOf(dcdr.entry.Entry):
    """
    A protocol entry representing a sequence of another protocol entry.
    """

    def __init__(self, name, child, length):
        dcdr.entry.Entry.__init__(self, name)
        self.child = child
        self._length = length
        assert isinstance(child, dcdr.entry.Entry)

    def _decode(self, data):
        length = int(self._length)
        for i in range(length):
            for item in self.child.decode(data):
                yield item

    def _encode(self, query, sequenceof):
        for child in sequenceof:
            for data in self.child.encode(query, child):
                yield data
