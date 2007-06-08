import bdec

class MissingInstanceError(bdec.DecodeError):
    """
    Error raised during encoding when a parent object doesn't have a named child object.
    """
    def __init__(self, parent, child):
        self.parent = parent
        self.child = child

    def __str__(self):
        return "object '%s' doesn't have child object '%s'" % (self.parent, self.child)

class Entry(object):
    """
    A decoder entry is an item in a protocol that can be decoded.
    """

    def __init__(self, name):
        self.name = name

    def _decode(self, data):
        """
        Decode the given protocol entry.

        Should return an iterable object for all of the 'embedded'
        protocol entries in the same form as Entry.decode.
        """
        raise NotImplementedError()

    def decode(self, data):
        """
        Decode this entry from input data.

        @param data The data to decode
        @return An iterator that returns (is_starting, Entry) tuples.
        """
        yield (True, self)
        for (is_starting, entry) in self._decode(data):
            yield (is_starting, entry)
        yield (False, self)

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
        
        Returns an iterator object for a series of data objects.
        """
        # This interface isn't too good; it requires us to load the _entire_ document
        # into memory. This is because it supports 'searching backwards', plus the
        # reference to the root element is kept. Maybe a push system would be better?
        #
        # Problem is, push doesn't work particularly well for bdec.output.instance, nor
        # for choice entries (where we need to re-wind...)

        try:
            context = query(parent_context, self.name)
        except MissingInstanceError:
            if not self.is_hidden():
                raise
            # The instance wasn't included in the input, but as it is hidden, we'll
            # keep using the current context.
            context = parent_context
        return self._encode(query, context)

    def is_hidden(self):
        """
        Is this a 'hidden' entry.

        Entries may be hidden for many reasons; for example, we don't want to
        see 'expected' results (that is, fields with data we expect, without
        which the decode would fail).
        """
        return self.name.endswith(':')
