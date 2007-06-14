import bdec.entry

class InvalidSequenceOfLength(bdec.DecodeError):
    def __init__(self, seq, length, data):
        self.sequenceof = seq
        self.length = length
        self.data = data

    def __str__(self):
        return "%s expected length of %i, got %i (%s)" % (self.sequenceof, self.length, len(self.data), self.data)

class SequenceOf(bdec.entry.Entry):
    """
    A protocol entry representing a sequence of another protocol entry.
    """

    def __init__(self, name, child, length):
        """
        A length of None will result in a 'greedy' sequence, which will
        decode as many child items as possible until decoding fails.
        """
        bdec.entry.Entry.__init__(self, name)
        self.child = child
        self._length = length
        assert isinstance(child, bdec.entry.Entry)

    def _decode(self, data):
        if self._length is not None:
            length = int(self._length)
            for i in range(length):
                for item in self.child.decode(data):
                    yield item
        else:
            # Greedy sequenceof; keep on decoding until it fails.
            while 1:
                iterator = self.child.decode(data.copy()) 
                try:
                    while 1:
                        iterator.next()
                except bdec.DecodeError:
                    break
                except StopIteration:
                    pass
                for item in self.child.decode(data):
                    yield item

    def _encode(self, query, sequenceof):
        if int(self._length) != len(sequenceof):
            raise InvalidSequenceOfLength(self, self._length, sequenceof)

        for child in sequenceof:
            for data in self.child.encode(query, child):
                yield data
