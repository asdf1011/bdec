
import bdec
import bdec.data as dt
from bdec.decode.entry import EntryDecoder
import bdec.inspect.chooser as chsr

class ChoiceDecoder(EntryDecoder):
    def __init__(self, *args, **kwargs):
        EntryDecoder.__init__(self, *args, **kwargs)
        self._chooser = None

    def _decode(self, data, context, name):
        if self._chooser is None:
            self._chooser = chsr.Chooser([child.decoder.entry for child in self.children])
        # Convert the list of entries to a list of children.
        possibles = []
        for entry in self._chooser.choose(data):
            for child in self.children:
                if child.decoder.entry is entry:
                    possibles.append(child)
                    break
            else:
                raise Exception('Failed to find child from possible option %s!' % entry)

        yield (True, name, self.entry, data, None)

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
                    for is_starting, child_name, entry, entry_data, value in self._decode_child(child, data.copy(), context.copy()):
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
        for is_starting, child_name, entry, data, value in self._decode_child(best_guess, data, context):
            yield is_starting, child_name, entry, data, value

        assert not failure_expected
        yield (False, name, self.entry, dt.Data(), None)
