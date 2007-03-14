
class Entry(object):
    """
    A decoder entry is an item in a protocol that can be decoded.
    """

    def __init__(self, name):
        self.name = name

    def _decode(self, data):
        """
        Decode the given protocol entry.

        Should return an iterable object for all of the 'embedded'
        protocol entries in the same form as Entry.decode.
        """
        raise NotImplementedError()

    def decode(self, data):
        """
        Decode this entry from input data.

        @param data The data to decode
        @return An iterator that returns (is_starting, Entry) tuples.
        """
        yield (True, self)
        for (is_starting, entry) in self._decode(data):
            yield (is_starting, entry)
        yield (False, self)

    def is_hidden(self):
        """
        Is this a 'hidden' entry.

        Entries may be hidden for many reasons; for example, we don't want to
        see 'expected' results (that is, fields with data we expect, without
        which the decode would fail).
        """
        return self.name.endswith(':')
