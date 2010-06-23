
from bdec import DecodeError
from bdec.encode.entry import EntryEncoder, MissingInstanceError

class ChoiceEncoder(EntryEncoder):
    def _get_context(self, query, parent, offset):
        try:
            return query(parent, self.entry, offset)
        except MissingInstanceError:
            # Choice entries can be completely hidden
            return parent

    def _encode(self, query, value):
        # We attempt to encode all of the embedded items, until we find
        # an encoder capable of doing it.
        best_guess = None
        best_guess_bits = 0
        for child in self.children:
            try:
                bits_encoded = 0
                for data in child.encoder.encode(query, value, 0):
                    bits_encoded += len(data)

                # We successfully encoded the entry!
                best_guess = child
                break
            except DecodeError:
                if best_guess is None or bits_encoded > best_guess_bits:
                    best_guess = child
                    best_guess_bits = bits_encoded

        return best_guess.encoder.encode(query, value, 0)
