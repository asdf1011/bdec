import bdec.data as dt
import bdec.entry

class InvalidSequenceOfCount(bdec.DecodeError):
    def __init__(self, seq, expected, actual):
        bdec.DecodeError.__init__(self, seq)
        self.sequenceof = seq
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return "%s expected count of %i, got %i" % (self.sequenceof, self.expected, self.actual)

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
        A count of None will result in a 'greedy' sequence, which will keep on
        decoding items until an entry in end_entries is decoded, or we run out
        of data.
        """
        bdec.entry.Entry.__init__(self, name, length, [child])
        self.count = count
        self.end_entries = end_entries
        assert isinstance(child, bdec.entry.Entry)

    def _loop(self, context, data):
        context['should end'] = False
        if self.count is not None:
            count = int(bdec.entry.hack_calculate_expression(self.count, context))
            if count < 0:
                raise NegativeSequenceofLoop(self, count)

            for i in range(count):
                yield i
        else:
            while 1:
                if context['should end']:
                    break
                try:
                    data.copy().pop(1)
                except dt.NotEnoughDataError:
                    # We ran out of data on a greedy sequence...
                    break
                yield None

    def _decode(self, data, context):
        yield (True, self, data)
        for i in self._loop(context, data):
            for item in self.children[0].decode(data, context):
                yield item
        yield (False, self, dt.Data())

    def _encode(self, query, parent):
        children = self._get_context(query, parent)

        count = 0
        for child in children:
            count += 1
            for data in self.children[0].encode(query, child):
                yield data

        if self.count is not None and int(self.count) != count:
            raise InvalidSequenceOfCount(self, self.count, count)

