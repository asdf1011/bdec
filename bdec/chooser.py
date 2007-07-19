
class Chooser:
    """
    Choose a protocol entry from a list of protocol entries that matches input data.
    """
    def __init__(self, entries):
        self._entries = entries

    def choose(self, data):
        """
        Return a list of possible entries that matches the input data.
        """
        return self._entries
