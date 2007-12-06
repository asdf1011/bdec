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

class MissingExpressionReferenceError(bdec.DecodeError):
    """
    An expression references an unknown entry.
    """
    def __init__(self, entry, missing):
        bdec.DecodeError.__init__(self, entry)
        self.missing_context = missing

    def __str__(self):
        return "%s needs '%s' to decode" % (self.entry, self.missing_context)


def is_hidden(name):
    """
    Is a name a 'hidden' name.

    Entries may be hidden for many reasons; for example, we don't want to
    see 'expected' results (that is, fields with data we expect, without
    which the decode would fail).
    """
    return name.endswith(':')

def _hack_recursive_replace_values(expression, context):
    # Walk the expression tree, and replace context items as appropriate.
    import bdec.spec.expression as expr
    if isinstance(expression, expr.ValueResult):
        name = expression.name
        expression.length = context[name]
    elif isinstance(expression, expr.LengthResult):
        expression.length = context[expression.name + " length"]
    elif isinstance(expression, expr.Delayed):
        _hack_recursive_replace_values(expression.left, context)
        _hack_recursive_replace_values(expression.right, context)

def hack_calculate_expression(expression, context):
    """
    A temporary hack to calculate expression values given a context.

    Will be removed in a future commit.
    """
    _hack_recursive_replace_values(expression, context)
    return int(expression)


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

def _hack_on_end_sequenceof(entry, length, context):
    context['should end'] = True
def _hack_on_length_referenced(entry, length, context):
    context[entry.name + ' length'] = length
def _hack_create_value_listener(name):
    def _on_value_referenced(entry, length, context):
        import bdec.field as fld
        import bdec.sequence as seq
        if isinstance(entry, fld.Field):
            context[name] = int(entry)
        elif isinstance(entry, seq.Sequence):
            context[name] = hack_calculate_expression(entry.value, context)
        else:
            raise Exception("Don't know how to read value of %s" % entry)
    return _on_value_referenced

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

        self._params = None
        self._parent_param_lookup = {}
        self._is_end_of_sequenceof = False

    def validate(self):
        """
        Validate all expressions contained within the entries.

        Throws MissingReferenceError if any expressions reference unknown instances.
        """
        if self._params is not None:
            return

        import bdec.inspect.param
        params = bdec.inspect.param.ParamLookup([self])
        self._set_params(params)

        # We need to raise an error as to missing parameters
        for param in params.get_params(self):
            if param.direction is param.IN:
                # TODO: We should instead raise the error from the context of the
                # child that needs the data.
                raise MissingExpressionReferenceError(self, param.name)

    def _set_params(self, lookup):
        """
        Set the parameters needed to decode this entry.
        """
        if self._params is not None:
            return
        self._params = lookup.get_params(self)
        for child in self.children:
            child_params = (param.name for param in lookup.get_params(child))
            our_params = (param.name for param in lookup.get_invoked_params(self, child))
            self._parent_param_lookup[child] = dict(zip(child_params, our_params))

        if lookup.is_end_sequenceof(self):
            self.add_listener(_hack_on_end_sequenceof)
        if lookup.is_value_referenced(self):
            # This is a bit of a hack... we need to use the correct (fully
            # specified) name. We'll lookup the parameter to get it.
            for param in self._params:
                if param.direction is param.OUT:
                    self.add_listener(_hack_create_value_listener(param.name))
        if lookup.is_length_referenced(self):
            self.add_listener(_hack_on_length_referenced)

        for child in self.children:
            child._set_params(lookup)

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

    def _decode_child(self, child, data, context):
        # Create the childs context from our data
        child_context = {}
        for param in child._params:
            if param.direction is param.IN:
                child_context[param.name] = context[self._parent_param_lookup[child][param.name]]

        # Do the decode
        for result in child.decode(data, child_context):
            yield result

        # Update our context with the output values from the childs context
        for param in child._params:
            if param.direction is param.OUT:
                if param.name == "should end":
                    try:
                        context[param.name] = child_context[param.name]
                    except KeyError:
                        # 'should end' is a hacked special case, as it may not always be set.
                        pass
                else:
                    context[self._parent_param_lookup[child][param.name]] = child_context[param.name]

    def _decode(self, data, child_context):
        """
        Decode the given protocol entry.

        Should return an iterable object for the entry (including all 'embedded'
        entries) in the same form as Entry.decode.
        """
        raise NotImplementedError()

    def decode(self, data, context={}):
        """
        Decode this entry from input data.

        @param data The data to decode
        @param context The context of our decode. Is a lookup of names to
            intger values.
        @return An iterator that returns (is_starting, Entry, data) tuples. The
            data when the decode is starting is the data available to be 
            decoded, and the data when the decode is finished is the data from
            this entry only (not including embedded entries).
        """
        self.validate()

        # Validate our context
        for param in self._params:
            if param.direction is param.IN:
                assert param.name in context, "Context to '%s' must include %s!" % (self, param.name)

        if self.length is not None:
            try:
                data = data.pop(hack_calculate_expression(self.length, context))
            except dt.DataError, ex:
                raise EntryDataError(self, ex)

        # Do the actual decode of this entry (and all embedded entries).
        length = 0
        for is_starting, entry, entry_data, value in self._decode(data, context):
            if not is_starting:
                length += len(entry_data)
            yield is_starting, entry, entry_data, value

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

    def _range(self, ignore_entries):
        """
        Can be implemented by derived classes to detect ranges.
        """
        return bdec.entry.Range()

    def range(self, ignore_entries=set()):
        """
        Return a Range instance indicating the length of this entry.

        If 'entry' is in 'ignore_entries', the length will be ignored.
        """
        if self in ignore_entries:
            # If an entry is recursive, we cannot predict how long it will be.
            return Range()

        import bdec.spec.expression
        result = None
        if self.length is not None:
            try:
                min = max = int(self.length)
                result = bdec.entry.Range(min, max)
            except bdec.spec.expression.UndecodedReferenceError:
                pass
        if result is None:
            ignore_entries.add(self)
            result = self._range(ignore_entries)
            ignore_entries.remove(self)
        return result
