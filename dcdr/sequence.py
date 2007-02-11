import dcdr.entry

class Sequence(dcdr.entry.Entry):
    """
    A sequence type protocol entry.

    A sequence protocol entry is made up of multiple other
    entry types, and they are decoded one after the other.
    All of the child protocol entries must be decoded for
    the sequence to successfully decode.
    """

    def __init__(self, name, children):
        dcdr.entry.Entry.__init__(self, name)
        self._children = children

    def _decode(self, data):
        for child in self._children:
            for embedded in child.decode(data):
                yield embedded
