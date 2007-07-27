import bdec.field as fld
import bdec.sequence as seq

class _UnknownData:
    """
    A class representing data with an unknown value.
    """
    UNKNOWN_LENGTH = 100000000

    def __init__(self, length=None):
        self._length = length

    def pop(self, length):
        if self._length is not None:
            assert self._length >= length
            self._length -= length
        return _UnknownData(length)

    def __len__(self):
        if self._length is None:
            return self.UNKNOWN_LENGTH
        return self._length

def _data_iter(entry):
    """
    Return an iterator to data objects in this protocol entry.
    """
    if isinstance(entry, fld.Field):
        if entry.expected is not None:
            yield entry.expected.copy()
        else:
            try:
                yield _UnknownData(int(entry.length))
            except:
                # Sometimes we are unable to determine the length of an item (for
                # example, if it refers to the decode value of another field).
                yield _UnknownData()
    elif isinstance(entry, seq.Sequence):
        for child in entry.children:
            for child_entry in _data_iter(child):
                yield child_entry
    else:
        # TODO: Implement drilling down into other entry types!
        yield _UnknownData()

def _differentiate(entries):
    """
    Differentiate between protocol entries.

    Returns a list of (offset, length, lookup, undistinguished) entries, where
    lookup is a dictionary mapping value -> entries, and undistinguished is a
    list of entries that don't distinguish themselves on this entry.
    """
    offset = 0
    data_options = [(list(_data_iter(entry)), entry) for entry in entries]
    while data_options:
        # Calculate the length of the next section of 'differentiable' protocol
        # section.
        length = min(len(data_list[0]) for data_list, entry in data_options)
        if length == _UnknownData.UNKNOWN_LENGTH:
            # We cannot differentiate any more...
            yield offset, 0, {}, [entry for data_list, entry in data_options]
            return

        # Get the values of all of the options for this data section
        lookup = {}
        undistinguished = []
        for data_list, entry in data_options[:]:
            data = data_list[0].pop(length)
            if len(data_list[0]) == 0:
                del data_list[0]
                if len(data_list) == 0:
                    # When an option has no more data to be matched, we use
                    # an unknown data object so it will still fall into
                    # the 'undistinguished' categories in later matches.
                    data_list.append(_UnknownData())

            if isinstance(data, _UnknownData):
                undistinguished.append(entry)
            else:
                lookup.setdefault(int(data), []).append(entry)

        yield offset, length, lookup, undistinguished
        offset += length


class _Options:
    """
    A class to recursively drill down into data, identifying potential options.
    """
    def __init__(self, options, start_bit):
        # Identify unique entries in the available options starting
        # at the bit offset.
        self._options = None
        for offset, length, lookup, undistinguished in _differentiate(options):
            if offset >= start_bit and lookup and length:
                # We found a range of bits that can be used to distinguish
                # between the diffent options
                self._start_bit = start_bit
                self._length = length
                self._lookup = {}
                self._fallback = _Options(undistinguished, start_bit + length)
                for value, entries in lookup.iteritems():
                    self._lookup[value] = _Options(entries + undistinguished, start_bit + length)
                break
        else:
            # We were unable to differentiate between the protocol entries.
            self._options = options

    def choose(self, data):
        """
        Return a list of possible entries that matches the input data.
        """
        if self._options is not None:
            # We are unable to narrow down the possibilities further.
            return self._options

        # We are able to potentially narrow down the possibilities based
        # on the input values.
        assert self._lookup
        copy = data.copy()
        copy.pop(self._start_bit)
        value = int(copy.pop(self._length))

        try:
            options = self._lookup[value]
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
