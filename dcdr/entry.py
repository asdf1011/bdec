
class Entry:
    """
    A decoder entry is an item in a protocol that can be decoded.
    """

    def __init__(self, name):
        self.name = name

    def decode(self, data, start, end):
        """
        Decode this entry from input data.

        @param data The data to decode
        @param start A function to be called when we start decoding
        @param end A function to be called when we finish decoding
        """
        raise NotImplementedError()
