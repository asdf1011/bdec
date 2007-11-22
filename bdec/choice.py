
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
        self._chooser = None

    def _decode(self, data, child_context):
        if self._chooser is None:
            import bdec.inspect.chooser as chsr
            self._chooser = chsr.Chooser(self.children)
        possibles = self._chooser.choose(data)

        yield (True, self, data, None)

        failure_expected = False
        if len(possibles) == 0:
            # None of the items match. In this case we want to choose
            # the 'best' failing option, so we'll examine all of the
            # children.
            possibles = self.children
            failure_expected = True

        if len(possibles) == 1:
            best_guess = possibles[0]
        else:
            # We have multiple possibilities. We'll decode them one
            # at a time until one of them succeeds; if none decode,
            # we'll re-raise the exception of the 'best guess'.
            #
            # Note: If we get in here, at best we'll decode the successfully
            # decoding item twice. This can have severe performance
            # implications if choices are embedded within choices (as
            # we get O(N^2) runtime cost).
            #
            # We should possibly emit a warning if we get in here (as it
            # indicates that the specification could be better written).
            best_guess = None
            best_guess_bits = 0
            for child in possibles:
                try:
                    bits_decoded = 0
                    for is_starting, entry, entry_data, value in child.decode(data.copy(), child_context):
                        if not is_starting:
                            bits_decoded += len(entry_data)

                    # We successfully decoded the entry!
                    best_guess = child
                    break
                except bdec.DecodeError:
                    if best_guess is None or bits_decoded > best_guess_bits:
                        best_guess = child
                        best_guess_bits = bits_decoded

        # Decode the best option.
        for is_starting, entry, data, value in best_guess.decode(data, child_context):
            yield is_starting, entry, data, value

        assert not failure_expected
        yield (False, self, dt.Data(), None)

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

    def range(self):
        minimum = min(child.range().min for child in self.children)
        maximum = max(child.range().max for child in self.children)
        return bdec.entry.Range(minimum, maximum)
