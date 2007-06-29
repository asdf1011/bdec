
import bdec.data as dt
import bdec.entry

class Choice(bdec.entry.Entry):
    """
    Implement an entry that can be one of many entries.

    The first entry to decode correctly will be used.
    """

    def __init__(self, name, children, length=None):
        bdec.entry.Entry.__init__(self, name, length, children)

        assert len(children) > 0
        for child in children:
            assert isinstance(child, bdec.entry.Entry)

    def _decode(self, data):
        yield (True, self, data)

        # We attempt to decode all of the embedded items. If
        # one of them succeeds, we'll use its results (otherwise
        # we'll re-raise the exception of the 'best guess'.
        best_guess = None
        best_guess_bits = 0
        for child in self.children:
            try:
                bits_decoded = 0
                for is_starting, entry, entry_data in child.decode(data.copy()):
                    if not is_starting:
                        bits_decoded += len(entry_data)

                # We successfully decoded the entry!
                best_guess = child
                break
            except bdec.DecodeError:
                if best_guess is None or bits_decoded > best_guess_bits:
                    best_guess = child
                    best_guess_bits = bits_decoded

        # Re-run the decode with the best guess
        # TODO: This algorithm has N^2 complexity! We should
        # re-use the existing decode results... This is not
        # trivial however, as the fields have state (the data
        # attribute) which we'd need to cache and reset.
        for is_starting, entry, data in best_guess.decode(data):
            yield is_starting, entry, data

        yield (False, self, dt.Data())

    def _encode(self, query, parent):
        # We attempt to encode all of the embedded items, until we find
        # an encoder capable of doing it.
        choice = self._get_context(query, parent)
        best_guess = None
        best_guess_bits = 0
        for child in self.children:
            try:
                bits_encoded = 0
                for data in child.encode(query, choice):
                    bits_encoded += len(data)

                # We successfully encoded the entry!
                best_guess = child
                break
            except bdec.DecodeError:
                if best_guess is None or bits_encoded > best_guess_bits:
                    best_guess = child
                    best_guess_bits = bits_encoded

        return best_guess.encode(query, choice)
