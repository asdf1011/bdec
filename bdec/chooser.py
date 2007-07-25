

class _Options:
    """
    A class to recursively drill down into data, identifying potential options.
    """
    def __init__(self, options, start_bit):
        # Identify unique entries in the available options starting
        # at the bit offset.
        self._lookup = {}
        self._fallback = None
        self._length = 0
        self._start_bit = 0

        self._options = options

    def choose(self, data):
        """
        Return a list of possible entries that matches the input data.
        """
        if self._options:
            # We are unable to narrow down the possibilities further.
            return self._options

        # We are able to potentially narrow down the possibilities based
        # on the input values.
        assert self._lookup
        copy = data.copy()
        copy.pop(self._start_bit)
        value = int(copy.pop(self._length))

        try:
            options = self._options[value]
        except KeyError:
            # The value present isn't one of the expected values; we'll
            # fallback to the options that could handle any value for
            # this bit offset.
            options = self._fallback
        return options.choose(data)

class Chooser(_Options):
    """
    Choose a protocol entry from a list of protocol entries that matches input data.

    This class attempts to quickly determine the type of protocol entry that can be
    decoded.
    """
    def __init__(self, entries):
        _Options.__init__(self, entries, 0)
