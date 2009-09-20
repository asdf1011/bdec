#   Copyright (C) 2008-2009 Henry Ludemann
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

import operator

import bdec
import bdec.data as dt
from bdec.expression import Expression, Constant, UndecodedReferenceError

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


class Child(object):
    """ A child is embedded in another entry."""
    def __init__(self, name, entry):
        self.name = name
        self.entry = entry

    def __repr__(self):
        return "%s '%s'" % (self.name, self.entry)

class Entry(object):
    """An entry is an item in a protocol that can be decoded.

    This class designed to be derived by other classes (not instantiated 
    directly).
    """

    def __init__(self, name, length, children, constraints=[]):
        """Construct an Entry instance.

        children -- A list of Entry instances.
        length -- Optionally specify the size in bits of the entry. Must be an
            instance of bdec.expression.Expression or an integer.
        constraints -- A list of constraints for the value of this entry.
        """
        if length is not None:
            if isinstance(length, int):
                length = Constant(length)
            assert isinstance(length, Expression)
        self.name = name
        self.length = length
        self._children = ()
        self.children = children

        self._params = None
        self._parent_param_lookup = {}
        self._is_end_sequenceof = False
        self._is_value_referenced = False
        self._is_length_referenced = False
        self.constraints = list(constraints)
        for constraint in self.constraints:
            assert getattr(constraint, 'check') is not None

    def _get_children(self):
        return self._children
    def _set_children(self, children):
        items = []
        for child in children:
            if isinstance(child, Child):
                items.append(child)
            else:
                # For convenience in the tests, we allow the children to be
                # assigned an array of Entry instances.
                items.append(Child(child.name, child))
        self._children = tuple(items)
    children = property(_get_children, _set_children)

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

    def _set_params(self, lookup):
        """
        Set the parameters needed to decode this entry.
        """
        if self._params is not None:
            return
        self._params = list(lookup.get_params(self))
        for child in self.children:
            child_params = (param.name for param in lookup.get_params(child.entry))
            our_params = (param.name for param in lookup.get_passed_variables(self, child))
            self._parent_param_lookup[child] = dict(zip(child_params, our_params))

        self._is_end_sequenceof = lookup.is_end_sequenceof(self)
        self._is_value_referenced = lookup.is_value_referenced(self)
        self._is_length_referenced = lookup.is_length_referenced(self)

        for child in self.children:
            child.entry._set_params(lookup)

    def _decode_child(self, child, data, context):
        """
        Decode a child entry.

        Creates a new context for the child, and after the decode completes,
        will update this entry's context.
        """
        assert isinstance(child, Child)

        # Create the childs context from our data
        child_context = {}
        for param in child.entry._params:
            if param.direction is param.IN:
                # The child's name may be different from what we are calling
                # it; adjust the name to be sure.
                child_context[param.name] = context[self._parent_param_lookup[child][param.name]]

        # Do the decode
        for result in child.entry.decode(data, child_context, child.name):
            yield result

        # Update our context with the output values from the childs context
        for param in child.entry._params:
            if param.direction is param.OUT:
                if param.name == "should end":
                    try:
                        context[param.name] = child_context[param.name]
                    except KeyError:
                        # 'should end' is a hacked special case, as it may not always be set.
                        pass
                else:
                    context[self._parent_param_lookup[child][param.name]] = child_context[param.name]

    def _decode(self, data, child_context, name):
        """
        Decode the given protocol entry.

        Should return an iterable object for the entry (including all 'child'
        entries) in the same form as Entry.decode.
        """
        raise NotImplementedError()

    def decode(self, data, context={}, name=None):
        """Return an iterator of (is_starting, name, Entry, data, value) tuples.

        The data returned is_starting==True the data available to be decoded,
        and the data returned when is_starting==False is the decode decoded by
        this entry (not including child entries).

        data -- An instance of bdec.data.Data to decode.
        context -- The context to decode in. Is a lookup of names to integer
           values.
        name -- The name to use for this entry. If None, uses self.name.
        """
        self.validate()
        if name is None:
            name = self.name

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
        for is_starting, name, entry, entry_data, value in self._decode(data, context, name):
            if not is_starting:
                length += len(entry_data)
            if not is_starting and entry is self:
                for constraint in self.constraints:
                    constraint.check(self, value, context)
            yield is_starting, name, entry, entry_data, value

        if self._is_end_sequenceof:
            context['should end'] = True
        if self._is_value_referenced:
            # The last entry to decode will be 'self', so 'value' will be ours.
            context[self.name] = int(value)
        if self._is_length_referenced:
            context[self.name + ' length'] = length
        if self.length is not None and len(data) != 0:
            raise DecodeLengthError(self, data)

    def _get_context(self, query, parent):
        # This interface isn't too good; it requires us to load the _entire_ document
        # into memory. This is because it supports 'searching backwards', plus the
        # reference to the root element is kept. Maybe a push system would be better?
        #
        # Problem is, push doesn't work particularly well for bdec.output.instance, nor
        # for choice entries (where we need to re-wind...)
        try:
            return query(parent, self)
        except MissingInstanceError:
            if self.is_hidden():
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

    def encode(self, query, value):
        """Return an iterator of bdec.data.Data instances.

        query -- Function to return a value to be encoded when given an entry
          instance and the parent entry's value. If the parent doesn't contain
          the expected instance, MissingInstanceError should be raised.
        value -- This entry's value that is to be encoded.
        """
        encode_length = 0
        value = self._fixup_value(value)

        for constraint in self.constraints:
            constraint.check(self, value, {})

        for data in self._encode(query, value):
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

        result = None
        if self.length is not None:
            try:
                min = max = self.length.evaluate({})
                result = bdec.entry.Range(min, max)
            except UndecodedReferenceError:
                pass
        if result is None:
            ignore_entries.add(self)
            result = self._range(ignore_entries)
            ignore_entries.remove(self)
        return result
