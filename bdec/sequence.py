import bdec.entry

class Sequence(bdec.entry.Entry):
    """
    A sequence type protocol entry.

    A sequence protocol entry is made up of multiple other
    entry types, and they are decoded one after the other.
    All of the child protocol entries must be decoded for
    the sequence to successfully decode.
    """

    def __init__(self, name, children):
        bdec.entry.Entry.__init__(self, name)
        self.children = children
        for child in children:
            assert isinstance(child, bdec.entry.Entry)

    def _decode(self, data):
        for child in self.children:
            for embedded in child.decode(data):
                yield embedded

    def _encode(self, query, structure):
        for child in self.children:
            for data in child.encode(query, structure):
                yield data
            
