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

class EncodeError(bdec.DecodeError):
    pass

class NotEnoughContextError(EncodeError):
    def __str__(self):
        return "%s needs context to encode" % self.entry


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

        children -- A list of Entry or Child instances.
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
        self._decoder = None

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
        if self._decoder is None:
            from bdec.decode import Decoder
            self._decoder = Decoder(self)

    def decode(self, data, context={}, name=None):
        """ Shortcut to bdec.decode.Decoder(self) """
        self.validate()
        return self._decoder.decode(data, context, name)

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
        context = {}

        length = None
        if self.length is not None:
            try:
                length = self.length.evaluate(context)
            except UndecodedReferenceError:
                raise NotEnoughContextError(self)

        for constraint in self.constraints:
            constraint.check(self, value, context)

        for data in self._encode(query, value):
            encode_length += len(data)
            yield data

        if length is not None and encode_length != length:
            raise DataLengthError(self, length, encode_length)

    def is_hidden(self):
        """Is this a 'hidden' entry."""
        return is_hidden(self.name)

    def __str__(self):
        return "%s '%s'" % (self.__class__.__name__.lower(), self.name)

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
