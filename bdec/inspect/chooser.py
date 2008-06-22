import logging

import bdec.choice as chc
import bdec.data as dt
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
        return self.__class__(length)

    def __len__(self):
        if self._length is None:
            return self.UNKNOWN_LENGTH
        return self._length

    def copy(self):
        return _UnknownData(self._length)

class _AnyData(_UnknownData):
    """A class representing a field that can take any data (with a specified length)."""
    def __init__(self, length):
        _UnknownData.__init__(self, length)

class _ChoiceData:
    """A class representing a fork in the data stream. """
    def __init__(self, options):
        self.options = options

    def copy(self):
        return self


def _data_iter(entry):
    """
    Return an iterator to data objects in this protocol entry.
    """
    if isinstance(entry, fld.Field):
        if entry.expected is not None:
            yield entry.expected.copy()
        else:
            import bdec.spec.expression as expr
            length = None
            min = max = None
            try:
                length = int(entry.length)
                if entry.min is not None:
                    min = int(entry.min)
                if entry.max is not None:
                    max = int(entry.max)
            except expr.UndecodedReferenceError:
                # If the length of a  field references the decoded value of
                # another field, we will not be able to calculate the length.
                pass

            MAX_RANGE_HANDLED = 100
            if (length is not None and min is not None and 
               max is not None and max - min < MAX_RANGE_HANDLED):
                # This field has a bit range; instead of just treating it as
                # unknown, handle every value in the range individually. This
                # allows us to lookup valid values for this field in a 
                # dictionary.
                options = [fld.Field("temp", length, expected=dt.Data.from_int_big_endian(value, length)) for value in xrange(min, max + 1)]
                yield _ChoiceData(options)
            else:
                if length is not None and min is None and max is None:
                    # When we know a field can accept any type of data, we are
                    # able to know that some entries _will_ decode (not just
                    # possibly decode).
                    yield _AnyData(length)
                else:
                    yield _UnknownData(length)
    elif isinstance(entry, seq.Sequence):
        for child in entry.children:
            for child_entry in _data_iter(child):
                yield child_entry
    elif isinstance(entry, chc.Choice):
        yield _ChoiceData(entry.children)
    else:
        # We don't attempt to use other entry types when differentiating, as
        # earlier fields should have been enough.
        yield _UnknownData()

class _IterCache:
    """A class to cache results from an iterator."""
    def __init__(self, iter):
        self._iter = iter
        self._cache = []

    def __iter__(self):
        i = 0
        while 1:
            if i == len(self._cache):
                if self._iter is None:
                    break
                try:
                    self._cache.append(self._iter.next())
                except StopIteration:
                    self._iter = None
                    break

            assert 0 <= i < len(self._cache)
            yield self._cache[i].copy()
            i = i + 1


class _JoinIters:
    """A class to join two iterator results into one."""
    def __init__(self, a, b):
        self._a = a
        self._b = b

    def __iter__(self):
        for a in self._a:
            yield a
        for b in self._b:
            yield b


class _EntryData:
    """
    Class to walk over a protcol entry's expected data stream.
    """
    def __init__(self, entry, data_iter):
        self._data_iter = iter(data_iter)
        self._data = self._data_iter.next()
        self.entry = entry

    def data_length(self):
        return len(self._data)

    def pop_data(self, length):
        result = self._data.pop(length)
        if len(self._data) == 0:
            try:
                self._data = self._data_iter.next()
            except StopIteration:
                # When an option has no more data to be matched, we use
                # an unknown data object so it will still fall into
                # the 'undistinguished' categories in later matches.
                #self._data = _UnknownData()
                self._data = None
        return result

    def should_fork(self):
        return isinstance(self._data, _ChoiceData)

    def fork(self):
        """
        Handle a fork in the data stream.

        Returns a list of _EntryData objects representing the different
        possible paths in the data stream.
        """
        assert self.should_fork()
        post_choice_iter = _IterCache(self._data_iter)
        for option in self._data.options:
            iter = _JoinIters(_data_iter(option), post_choice_iter)
            yield _EntryData(self.entry, iter)

def _can_differentiate(lookup, fallback):
    """Test to see if a lookup differentiates itself from other options."""
    current_entries = None
    for value, entries in lookup.iteritems():
        entry_set = set(entries)
        if current_entries is None:
            current_entries = entry_set
        elif current_entries != entry_set:
            # This items entries differ from another items entries (and so can
            # differentiate).
            return True

        if not set(fallback).issubset(entry_set):
            return True

    # This bit range cannot be used for differentiation, as all of
    # the keyed options (and the fallback) have the same entries.
    return False

def _differentiate(entries):
    """
    Differentiate between protocol entries.

    Returns an iterator to (offset, length, lookup, undistinguished, decoded, 
    possibles) entries, where lookup is a dictionary mapping 
    value -> entries, and undistinguished is a list of entries that don't
    distinguish themselves on this entry.
    """
    offset = 0
    data_options = [_EntryData(entry, _data_iter(entry)) for entry in entries]

    # We need to keep track of entries that have successfully decoded, and
    # those that may have decoded.
    successful = []
    possible = []
    have_new_success = False
    while len(data_options) > 1:
        test_for_forks = True
        while test_for_forks:
            for option in data_options[:]:
                if option.should_fork():
                    data_options.remove(option)
                    data_options.extend(option.fork())
                    break
            else:
                test_for_forks = False

        # Calculate the length of the next section of 'differentiable' protocol
        # section.
        length = min(entry.data_length() for entry in data_options)
        if length == _UnknownData.UNKNOWN_LENGTH:
            # We cannot differentiate any more...
            break

        # Get the values of all of the options for this data section
        lookup = {}
        undistinguished = []
        for entry in data_options:
            data = entry.pop_data(length)

            if isinstance(data, _AnyData):
                undistinguished.append(entry.entry)
            elif isinstance(data, _UnknownData):
                # This entry _may_ have been successfuly...
                undistinguished.append(entry.entry)
                if entry.entry not in possible:
                    possible.append(entry.entry)
            else:
                lookup.setdefault(int(data), []).append(entry.entry)

        if have_new_success or _can_differentiate(lookup, undistinguished + successful + possible):
            # We also should notify if we have a new item in the successful (or possible) list...
            yield offset, length, lookup, undistinguished, successful, possible
        have_new_success = False

        for entry in data_options[:]:
            if entry._data is None:
                if entry.entry not in possible:
                    # This entry has finished decoding. If we _know_ it has
                    # finished decoding, blah blah blah
                    have_new_success = True
                    successful.append(entry.entry)
                data_options.remove(entry)
        offset += length

    # Unable to differentiate any more; give one more result with all
    # of the current possible option.
    yield offset, 0, {}, [entry.entry for entry in data_options], successful, possible


class Chooser:
    def __init__(self, entries):
        self._entries = entries
        self._iter = _differentiate(list(entries))
        self._cached = []

    def _differentiate(self):
        for i in self._cached:
            yield i
        while 1:
            i = self._iter.next()
            offset, length, lookup, undistinguished, successful, possible = i
            self._cached.append((offset, length, lookup.copy(), undistinguished[:], successful[:], possible[:]))
            yield i

    def choose(self, data):
        options = list(self._entries)
        current_offset = 0
        copy = data.copy()
        for offset, length, lookup, undistinguished, successful, possible in self._differentiate():
            if len(options) <= 1:
                break

            # Get the value of the data at this location
            assert offset >= current_offset
            try:
                copy.pop(offset - current_offset)
                value = int(copy.pop(length))
                current_offset = offset + length
            except dt.NotEnoughDataError:
                # We don't have enough data left for this option; reduce
                # the possibles to those that have finished decoding.
                options = [option for option in options if option in set(successful + possible)]
                break

            # Check to see if we have a successful item, and remove any items
            # after that item (as they cannot succeed).
            for i, option in enumerate(options):
                if option in successful:
                    # We found a successful item; no options after this can 
                    # succeed (as they are a lower priority).
                    del options[i+1:]
                    break

            if lookup and length:
                # We found a range of bits that can be used to distinguish
                # between the diffent options.
                fallback_entries = set(undistinguished + successful + possible)
                filter = successful + possible + undistinguished
                try:
                    filter += lookup[value]
                except KeyError:
                    pass
                options = [option for option in options if option in filter]
        return options
