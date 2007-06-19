import bdec.entry

class Sequence(bdec.entry.Entry):
    """
    A sequence type protocol entry.

    A sequence protocol entry is made up of multiple other
    entry types, and they are decoded one after the other.
    All of the child protocol entries must be decoded for
    the sequence to successfully decode.

    A sequence object may be assigned a value, derived from
    the child elements. This allows techniques such as
    lookup tables, and alternate integer encoding methods.
    """

    def __init__(self, name, children, value=None):
        bdec.entry.Entry.__init__(self, name)
        self.children = children
        self.value = value
        assert len(children) > 0
        for child in children:
            assert isinstance(child, bdec.entry.Entry)

    def _decode(self, data):
        for child in self.children:
            for embedded in child.decode(data):
                yield embedded

    def _encode(self, query, parent):
        structure = self._get_context(query, parent)
        for child in self.children:
            for data in child.encode(query, structure):
                yield data
            
