
import dcdr.entry
import dcdr.field as fld

class ChoiceDecodeError(dcdr.DecodeError):
    """
    One of the entries under the choice failed to decode.

    Ideally we should raise the decode error of the one 
    that decoded the most, but this is easier for now.
    """
    pass

class Choice(dcdr.entry.Entry):
    """
    Implement an entry that can be one of many entries.

    The first entry to decode correctly will be used.
    """

    def __init__(self, name, children):
        dcdr.entry.Entry.__init__(self, name)

        assert len(children) > 0
        self.children = children

    def _decode(self, data):
        # We attempt to decode all of the embedded items. If
        # one of them succeeds, we'll use its results (otherwise
        # we'll re-raise the exception of the 'best guess'.
        best_guess = None
        best_guess_bits = 0
        best_guess_result = []
        best_guess_exception = None
        for child in self.children:
            try:
                result = []
                bits_decoded = 0
                for is_starting, entry in child.decode(data.copy()):
                    result.append((is_starting, entry))
                    if not is_starting and isinstance(entry, fld.Field):
                        bits_decoded += len(entry.data)

                # We successfully decoded the entry!
                break
            except dcdr.DecodeError, ex:
                if best_guess is None or bits_decoded > best_guess_bits:
                    best_guess = child
                    best_guess_bits = bits_decoded
                    best_guess_result = result
                    best_guess_exception = ex
        else:
            # We failed to decode any items in the choice. As we
            # know the 'best guess' decoded, we could re-run that
            # decode to get the error; this could lead to N^2 
            # complexity however if multiple failing choices are
            # embedded in each other. To keep N complexity we'll
            # reuse the best guess results...
            data.pop(best_guess_bits)
            for is_starting, entry in best_guess_result:
                yield (is_starting, entry)
            raise best_guess_exception

        # We successfully decoded the data! Instead of decoding
        # it all again (which can lead to N^2 complexity as
        # choices become embedded in choices), we'll just pop
        # the data from the input buffer, and return the result.
        assert child is not None
        data.pop(bits_decoded)
        for is_starting, entry in result:
            yield is_starting, entry
