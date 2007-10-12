import bdec
import bdec.data as dt

class MissingInstanceError(bdec.DecodeError):
    """
    Error raised during encoding when a parent object doesn't have a named child object.
    """
    def __init__(self, parent, child):
        bdec.DecodeError.__init__(self, child)
        self.parent = parent
        self.child = child

    def __str__(self):
        return "object '%s' doesn't have child object '%s'" % (self.parent, self.child.name)

class EntryDataError(bdec.DecodeError):
    def __init__(self, entry, ex):
        bdec.DecodeError.__init__(self, entry)
        self.ex = ex

    def __str__(self):
        return "%s - %s" % (self.entry, self.ex)

class DecodeLengthError(bdec.DecodeError):
    def __init__(self, entry, unused):
        bdec.DecodeError.__init__(self, entry)
        self.unused = unused

    def __str__(self):
        return "'%s' left %i bits of data undecoded (%s)" % (self.entry, len(self.unused), self.unused.get_binary_text())

class DataLengthError(bdec.DecodeError):
    """
    Encoded data has the wrong length
    """
    def __init__(self, entry, length, data):
        bdec.DecodeError.__init__(self, entry)
        self.length = length
        self.data = data

    def __str__(self):
        return "%s expected length %i, got length %i (%s)" % (self.entry, self.length, len(self.data), self.data.get_binary_text())

def is_hidden(name):
    """
    Is a name a 'hidden' name.

    Entries may be hidden for many reasons; for example, we don't want to
    see 'expected' results (that is, fields with data we expect, without
    which the decode would fail).
    """
    return name.endswith(':')

class Range:
    """
    Class representing the possible length of a protocol entry.
    
    The possible in range is inclusive of min and max.
    """
    MAX = 100000000
    def __init__(self, min=0, max=MAX):
        assert min <= max
        self.min = min
        self.max = max

    def __add__(self, other):
        min = self.min + other.min
        if self.max is self.MAX or other.max is self.MAX:
            max = self.MAX
        else:
            max = self.max + other.max
        return Range(min, max)

class Entry(object):
    """
    A decoder entry is an item in a protocol that can be decoded.

    An entry can have a length; if so, the decode size of that entry
    must match.
    """

    def __init__(self, name, length, embedded):
        self.name = name
        self._listeners = []
        self.length = length
        self.children = embedded

    def add_listener(self, listener):
        """
        Add a listener to be called when the entry successfully decodes.

        The listener will be called with this entry, and the amount of data
        decoded as part of this entry (ie: this entry, and all of its
        children), and the context of this entry.

        Note that the listener will be called for every internal decode, not
        just the ones that are propageted to the user (for example, if an
        entry is in a choice that later fails to decode, the listener will
        still be notified).
        """
        self._listeners.append(listener)

    def _decode(self, data, child_context):
        """
        Decode the given protocol entry.

        Should return an iterable object for the entry (including all 'embedded'
        entries) in the same form as Entry.decode.
        """
        raise NotImplementedError()

    def decode(self, data, context=0):
        """
        Decode this entry from input data.

        @param data The data to decode
        @param context The depth of this protocol entry. Any child entries
            will have a context of 'context + 1'.
        @return An iterator that returns (is_starting, Entry, data) tuples. The
            data when the decode is starting is the data available to be 
            decoded, and the data when the decode is finished is the data from
            this entry only (not including embedded entries).
        """
        if self.length is not None:
            try:
                data = data.pop(int(self.length))
            except dt.DataError, ex:
                raise EntryDataError(self, ex)

        length = 0
        for is_starting, entry, entry_data in self._decode(data, context + 1):
            if not is_starting:
                length += len(entry_data)
            yield is_starting, entry, entry_data

        if self.length is not None and len(data) != 0:
            raise DecodeLengthError(self, data)

        for listener in self._listeners:
            listener(self, length, context)

    def _get_context(self, query, parent):
        # This interface isn't too good; it requires us to load the _entire_ document
        # into memory. This is because it supports 'searching backwards', plus the
        # reference to the root element is kept. Maybe a push system would be better?
        #
        # Problem is, push doesn't work particularly well for bdec.output.instance, nor
        # for choice entries (where we need to re-wind...)

        try:
            context = query(parent, self)
        except MissingInstanceError:
            if not self.is_hidden():
                raise
            # The instance wasn't included in the input, but as it is hidden, we'll
            # keep using the current context.
            context = parent
        return context

    def _encode(self, query, context):
        """
        Encode a data source, with the context being the data to encode.
        """
        raise NotImplementedError()

    def encode(self, query, parent_context):
        """
        Encode a data source.

        Sub-items will be queried by calling 'query' with a name and the context
        object. This query should raise a MissingInstanceError if the instance
        could not be found.
        
        Should return an iterable object for SequenceOf entries.
        """
        encode_length = 0
        for data in self._encode(query, parent_context):
            encode_length += len(data)
            yield data

        if self.length is not None and encode_length != int(self.length):
            raise DataLengthError(self, int(self.length), data)

    def is_hidden(self):
        """
        Is this a 'hidden' entry.
        """
        return is_hidden(self.name)

    def __str__(self):
        return "%s '%s'" % (self.__class__, self.name)

    def __repr__(self):
        return "%s '%s'" % (self.__class__, self.name)

    def range(self):
        return Range()
