
import bdec

class DataLengthError(bdec.DecodeError):
    """Encoded data has the wrong length."""
    def __init__(self, entry, expected, actual):
        bdec.DecodeError.__init__(self, entry)
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return "%s expected length %i, got length %i" % (self.entry, self.expected, self.actual)

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


class Child:
    def __init__(self, name, encoder):
        self.name = name
        self.encoder = encoder

    def __str__(self):
        return str(self.encoder)

class EntryEncoder:
    def __init__(self, entry):
        self.entry = entry
        self.children = []

    def _get_context(self, query, parent, offset):
        # This interface isn't too good; it requires us to load the _entire_ document
        # into memory. This is because it supports 'searching backwards', plus the
        # reference to the root element is kept. Maybe a push system would be better?
        #
        # Problem is, push doesn't work particularly well for bdec.output.instance, nor
        # for choice entries (where we need to re-wind...)
        try:
            return query(parent, self.entry, offset)
        except MissingInstanceError:
            if self.entry.is_hidden():
                return None
            raise

    def get_context(self, query, parent):
        return self._get_context(query, parent)

    def _encode(self, query, value):
        """
        Encode a data source, with the context being the data to encode.
        """
        raise NotImplementedError()

    def _fixup_value(self, value):
        """
        Allow entries to modify the value to be encoded.
        """
        return value

    def encode(self, query, value, offset):
        """Return an iterator of bdec.data.Data instances.

        query -- Function to return a value to be encoded when given an entry
          instance and the parent entry's value. If the parent doesn't contain
          the expected instance, MissingInstanceError should be raised.
        value -- This entry's value that is to be encoded.
        """
        value = self._get_context(query, value, offset)

        encode_length = 0
        value = self._fixup_value(value)
        context = {}

        length = None
        if self.entry.length is not None:
            try:
                length = self.entry.length.evaluate(context)
            except UndecodedReferenceError:
                raise NotEnoughContextError(self)

        for constraint in self.entry.constraints:
            constraint.check(self.entry, value, context)

        for data in self._encode(query, value):
            encode_length += len(data)
            yield data

        if length is not None and encode_length != length:
            raise DataLengthError(self.entry, length, encode_length)

    def __str__(self):
        return 'encoder for %s' % self.entry
