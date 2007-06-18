import bdec.entry

class InvalidSequenceOfLength(bdec.DecodeError):
    def __init__(self, seq, length, data):
        bdec.DecodeError.__init__(self, seq)
        self.sequenceof = seq
        self.length = length
        self.data = data

    def __str__(self):
        return "%s expected length of %i, got %i (%s)" % (self.sequenceof, self.length, len(self.data), self.data)

class NegativeSequenceofLoop(bdec.DecodeError):
    def __init__(self, seq, length):
        bdec.DecodeError.__init__(self, seq)
        self.length = length

    def __str__(self):
        return "%s asked to loop %i times!" % (self.entry, self.length)

class SequenceOf(bdec.entry.Entry):
    """
    A protocol entry representing a sequence of another protocol entry.
    """
    STOPPED = "stopped"
    ITERATING = "iterating"
    STOPPING = "stopping"

    def __init__(self, name, child, length):
        """
        A length of None will result in a 'greedy' sequence, which will
        keep on decoding items (until 'break' is called).
        """
        bdec.entry.Entry.__init__(self, name)
        self.child = child
        self._length = length
        self._state = self.STOPPED
        assert isinstance(child, bdec.entry.Entry)

    def stop(self):
        """
        Stop a currently iterating sequence of.
        """
        assert self._state is not self.STOPPED
        self._state = self.STOPPING

    def _loop(self):
        if self._length is not None:
            length = int(self._length)
            if length < 0:
                raise NegativeSequenceofLoop(self, length)

            for i in range(length):
                yield i
        else:
            while 1:
                yield None

    def _decode(self, data):
        self._state = self.ITERATING
        for i in self._loop():
            for item in self.child.decode(data):
                yield item

            if self._state is self.STOPPING:
                break
        self._state = self.STOPPED

    def _encode(self, query, sequenceof):
        if self._length is not None and int(self._length) != len(sequenceof):
            raise InvalidSequenceOfLength(self, self._length, sequenceof)

        for child in sequenceof:
            for data in self.child.encode(query, child):
                yield data
