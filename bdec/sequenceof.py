import bdec.entry

class InvalidSequenceOfCount(bdec.DecodeError):
    def __init__(self, seq, count, data):
        bdec.DecodeError.__init__(self, seq)
        self.sequenceof = seq
        self.count = count
        self.data = data

    def __str__(self):
        return "%s expected count of %i, got %i (%s)" % (self.sequenceof, self.count, len(self.data), self.data)

class NegativeSequenceofLoop(bdec.DecodeError):
    def __init__(self, seq, count):
        bdec.DecodeError.__init__(self, seq)
        self.count = count

    def __str__(self):
        return "%s asked to loop %i times!" % (self.entry, self.count)

class SequenceOf(bdec.entry.Entry):
    """
    A protocol entry representing a sequence of another protocol entry.
    """
    STOPPED = "stopped"
    ITERATING = "iterating"
    STOPPING = "stopping"

    def __init__(self, name, child, count):
        """
        A count of None will result in a 'greedy' sequence, which will
        keep on decoding items (until 'break' is called).
        """
        bdec.entry.Entry.__init__(self, name)
        self.child = child
        self._count = count
        self._state = self.STOPPED
        assert isinstance(child, bdec.entry.Entry)

    def stop(self):
        """
        Stop a currently iterating sequence of.
        """
        assert self._state is not self.STOPPED
        self._state = self.STOPPING

    def _loop(self):
        if self._count is not None:
            count = int(self._count)
            if count < 0:
                raise NegativeSequenceofLoop(self, count)

            for i in range(count):
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

    def _encode(self, query, parent):
        sequenceof = self._get_context(query, parent)
        if self._count is not None and int(self._count) != len(sequenceof):
            raise InvalidSequenceOfCount(self, self._count, sequenceof)

        for child in sequenceof:
            for data in self.child.encode(query, child):
                yield data
