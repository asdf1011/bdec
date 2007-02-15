import dcdr.entry

class SequenceOf(dcdr.entry.Entry):
    """
    A protocol entry representing a sequence of another protocol entry.
    """

    def __init__(self, name, child, length):
        dcdr.entry.Entry.__init__(self, name)
        self.child = child
        self._length = length

    def _decode(self, data):
        length = self._length()
        for i in range(length):
            for item in self.child.decode(data):
                yield item
