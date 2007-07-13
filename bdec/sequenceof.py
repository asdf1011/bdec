import bdec.data as dt
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

    def __init__(self, name, child, count, length=None, end_entries=[]):
        """
        A count of None will result in a 'greedy' sequence, which will
        keep on decoding items (until an entry in end_entries is decoded).
        """
        bdec.entry.Entry.__init__(self, name, length, [child])
        self._count = count
        self._end_entries = end_entries
        assert isinstance(child, bdec.entry.Entry)

    def _loop(self, child_context):
        # At the moment this 'listener' is never removed, and it doesn't work
        # for stack based notifications (eg: recursive sequenceof entries,
        # where only the outer entry wants to be notified).
        stop = [False]
        for entry, offset in self._end_entries:
            def break_sequence(entry, length, context):
                # The entry we have been waiting for has triggered. In the event
                # that we are a recursive entry, we need to make sure that is
                # the _correct_ instance of the entry that we are waiting on.
                if context - child_context == offset:
                    stop[0] = True
            entry.add_listener(break_sequence)

        self._stop = False
        if self._count is not None:
            count = int(self._count)
            if count < 0:
                raise NegativeSequenceofLoop(self, count)

            for i in range(count):
                yield i
        else:
            while 1:
                if stop[0]:
                    break
                yield None

    def _decode(self, data, child_context):
        yield (True, self, data)
        for i in self._loop(child_context):
            for item in self.children[0].decode(data, child_context):
                yield item
        yield (False, self, dt.Data())

    def _encode(self, query, parent):
        sequenceof = self._get_context(query, parent)
        if self._count is not None and int(self._count) != len(sequenceof):
            raise InvalidSequenceOfCount(self, self._count, sequenceof)

        for child in sequenceof:
            for data in self.children[0].encode(query, child):
                yield data
