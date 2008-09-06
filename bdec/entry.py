#   Copyright (C) 2008 Henry Ludemann
#
#   This file is part of the bdec decoder library.
#
#   The bdec decoder library is free software; you can redistribute it
#   and/or modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   The bdec decoder library is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, see
#   <http://www.gnu.org/licenses/>.

"""
The bdec.entry module defines the core entry class (bdec.entry.Entry) and 
errors (derived from bdec.DecodeError) common to all entry types.
"""

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
    """Error raised when an error was found with the entries data.
    
    For example, not enough data was available to decode this entry."""
    def __init__(self, entry, ex):
        bdec.DecodeError.__init__(self, entry)
        self.ex = ex

    def __str__(self):
        return "%s - %s" % (self.entry, self.ex)

class DecodeLengthError(bdec.DecodeError):
    """An entry failed to decode all of the data that was allocated to it."""
    def __init__(self, entry, unused):
        bdec.DecodeError.__init__(self, entry)
        self.unused = unused

    def __str__(self):
        return "'%s' left %i bits of data undecoded (%s)" % (self.entry, len(self.unused), self.unused.get_binary_text())

class DataLengthError(bdec.DecodeError):
    """Encoded data has the wrong length."""
    def __init__(self, entry, expected, actual):
        bdec.DecodeError.__init__(self, entry)
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return "%s expected length %i, got length %i" % (self.entry, self.expected, self.actual)

class MissingExpressionReferenceError(bdec.DecodeError):
    """An expression references an unknown entry."""
    def __init__(self, entry, missing):
        bdec.DecodeError.__init__(self, entry)
        self.missing_context = missing

    def __str__(self):
        return "%s needs '%s' to decode" % (self.entry, self.missing_context)


def is_hidden(name):
    """Is a name a 'hidden' name.

    Entries may be hidden for many reasons; for example, we don't want to
    see 'expected' results (that is, fields with data we expect, without
    which the decode would fail).
    """
    return len(name) == 0 or name.endswith(':')


class Range:
    """Class representing the possible length of a protocol entry.
    
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
            context[name] = entry.value.evaluate(context)
        else:
            raise Exception("Don't know how to read value of %s" % entry)
    return _on_value_referenced

class Entry(object):
    """An entry is an item in a protocol that can be decoded.

    This class designed to be derived by other classes (not instantiated 
    directly).
    """

    def __init__(self, name, length, children):
        """Construct an Entry instance.

        length -- Optionally specify the size in bits of the entry. Must be an
            instance of bdec.spec.expression.Expression or an integer.
        """
        from bdec.spec.expression import Expression, Constant
        if length is not None:
            if isinstance(length, int):
                length = Constant(length)
            assert isinstance(length, Expression)
        self.name = name
        self._listeners = []
        self.length = length
        self.children = children

        self._params = None
        self._parent_param_lookup = {}

    def validate(self):
        """
        Validate all expressions contained within the entries.

        Throws MissingReferenceError if any expressions reference unknown instances.
        """
        if self._params is not None:
            return

        import bdec.inspect.param
        end_entry_params = bdec.inspect.param.EndEntryParameters([self])
        expression_params = bdec.inspect.param.ExpressionParameters([self])
        params = bdec.inspect.param.CompoundParameters([end_entry_params, expression_params])
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
        self._params = list(lookup.get_params(self))
        for child in self.children:
            child_params = (param.name for param in lookup.get_params(child))
            our_params = (param.name for param in lookup.get_passed_variables(self, child))
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
        """
        Decode a child entry.

        Creates a new context for the child, and after the decode completes,
        will update this entry's context.
        """
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

        Should return an iterable object for the entry (including all 'child'
        entries) in the same form as Entry.decode.
        """
        raise NotImplementedError()

    def decode(self, data, context={}):
        """Return an iterator of (is_starting, Entry, data, value) tuples.

        The data returned is_starting==True the data available to be decoded,
        and the data returned when is_starting==False is the decode decoded by
        this entry (not including child entries).

        data -- An instance of bdec.data.Data to decode.
        context -- The context to decode in. Is a lookup of names to integer
           values.

        """
        self.validate()

        # Validate our context
        for param in self._params:
            if param.direction is param.IN:
                assert param.name in context, "Context to '%s' must include %s!" % (self, param.name)

        if self.length is not None:
            try:
                data = data.pop(self.length.evaluate(context))
            except dt.DataError, ex:
                raise EntryDataError(self, ex)

        # Do the actual decode of this entry (and all child entries).
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
        """Return an iterator of bdec.data.Data instances.

        query -- Function to return a value to be encoded when given an entry
          instance and the parent entry's value. If the parent doesn't contain
          the expected instance, MissingInstanceError should be raised.
        parent_context -- The value of the parent of this instance.
        """
        encode_length = 0
        for data in self._encode(query, parent_context):
            encode_length += len(data)
            yield data

        if self.length is not None and encode_length != self.length.evaluate({}):
            raise DataLengthError(self, self.length.evaluate({}), encode_length)

    def is_hidden(self):
        """Is this a 'hidden' entry."""
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
        """Return a Range instance indicating the length of this entry.

        ignore_entries -- If self is in ignore_entries, a default Range 
           instance will be returned. 'self' and all child entries will
           be added to ignore_entries.
        """
        if self in ignore_entries:
            # If an entry is recursive, we cannot predict how long it will be.
            return Range()

        import bdec.spec.expression
        result = None
        if self.length is not None:
            try:
                min = max = self.length.evaluate({})
                result = bdec.entry.Range(min, max)
            except bdec.spec.expression.UndecodedReferenceError:
                pass
        if result is None:
            ignore_entries.add(self)
            result = self._range(ignore_entries)
            ignore_entries.remove(self)
        return result
