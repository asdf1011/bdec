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

import operator

import bdec.choice as chc
from bdec.constraints import Equals, Maximum, Minimum
import bdec.data as dt
import bdec.entry as ent
import bdec.expression as expr
import bdec.field as fld
import bdec.sequence as seq
import bdec.sequenceof as sof

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

def _get_constraint(entry, constraint_type):
    for constraint in entry.constraints:
        if isinstance(constraint, constraint_type):
            try:
                return constraint.limit.evaluate({})
            except expr.UndecodedReferenceError:
                # We don't know the value for this entry, and so cannot use it.
                return
    return None

class _ProtocolStream:
    _MAX_FIELD_RANGE = 100
    def __init__(self, entry, parent=None, parent_offset=None):
        min = _get_constraint(entry, Minimum)
        max = _get_constraint(entry, Maximum)
        if min is not None and max is not None and max - min < self._MAX_FIELD_RANGE and entry.length is not None:
            # When we have a ranged field, it can be conveniant to 'key' on the
            # possible values. This allows early outs...
            options = []
            for i in range(min, max + 1):
                value = dt.Data.from_int_big_endian(i, entry.length.evaluate({}))
                options.append(fld.Field(entry.name, entry.length, format=fld.Field.INTEGER, constraints=[Equals(value)]))
            self.entry = chc.Choice('mock %s' % entry.name, options)
        else:
            self.entry = entry
        self.data = self._create_data()
        self._parent = parent
        self._parent_offset = parent_offset

    def _next(self, offset):
        """Walk up the tree looking for the next child.
        
        Takes the child offset to walk into. """
        if isinstance(self.entry, seq.Sequence):
            if offset < len(self.entry.children):
                # There are still child items in this sequence, so return the
                # next child.
                return [_ProtocolStream(self.entry.children[offset].entry, self, offset)]
            assert offset == len(self.entry.children)
        elif isinstance(self.entry, chc.Choice):
            # The next entry of the choice is all of its children. After that
            # we must go back up to the parent.
            if offset == 0:
                return [_ProtocolStream(child.entry, self, 0) for child in self.entry.children]

        # We don't have any more embedded items; go back up to the parent.
        if self._parent is None:
            return []
        return self._parent._next(self._parent_offset+1)

    def __eq__(self, other):
        if self.entry is not other.entry:
            return False
        if self._parent is not other._parent:
            return False
        if self._parent_offset != other._parent_offset:
            return False
        return self.data == other.data

    def next(self):
        """Return an iterator to _ProtocolStream items"""
        return self._next(0)

    def _create_data(self):
        """Return a data instance, or None if one doesn't exist for this entry."""
        if isinstance(self.entry, fld.Field):
            value = _get_constraint(self.entry, Equals)
            try:
                if value is not None:
                    def query(context, entry):
                        raise bdec.entry.MissingInstanceError()
                    data = reduce(operator.add, self.entry.encode(query, value))
                    return data
            except ent.NotEnoughContextError:
                # We can't encode this entry; see if we know how long it is.
                pass

            length = None
            try:
                length = self.entry.length.evaluate({})
            except expr.UndecodedReferenceError:
                # If the length of a  field references the decoded value of
                # another field, we will not be able to calculate the length.
                pass

            if length is not None and not self.entry.constraints:
                # When we know a field can accept any type of data, we are
                # able to know that some entries _will_ decode (not just
                # possibly decode).
                return _AnyData(length)
            else:
                return _UnknownData(length)
        elif isinstance(self.entry, sof.SequenceOf):
            return _UnknownData()
        elif self.entry.constraints:
            # This entry has unknown constraints... return an unkown data object.
            return _UnknownData(0)
        else:
            # This entry contains no data (but its children might)...
            return dt.Data()


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

    # We need to keep track of entries that have successfully decoded, and
    # those that may have decoded.
    successful = []
    possible = []
    have_new_success = False
    options = [(entry, _ProtocolStream(entry)) for entry in entries]
    while len(options) > 1:
        length = min(len(option.data) for entry, option in options)

        # Calculate the length of the next section of 'differentiable' protocol
        # section.
        if length == _UnknownData.UNKNOWN_LENGTH:
            # We cannot differentiate any more...
            break

        # Get the values of all of the options for this data section
        lookup = {}
        undistinguished = []
        for entry, option in options:
            data = option.data.pop(length)
            if isinstance(data, _AnyData):
                undistinguished.append(entry)
            elif isinstance(data, _UnknownData):
                # This entry _may_ have been successfuly decoded...
                undistinguished.append(entry)
                if entry not in possible:
                    possible.append(entry)
            elif data:
                lookup.setdefault(int(data), []).append(entry)

        if have_new_success or _can_differentiate(lookup, undistinguished + successful + possible):
            # We also should notify if we have a new item in the successful (or possible) list...
            yield offset, length, lookup, undistinguished, successful, possible
        have_new_success = False

        for entry, option in options[:]:
            if len(option.data) == 0:
                next = list((entry, next) for next in option.next())
                options.remove((entry, option))
                for item in next:
                    if item not in options:
                        # We found a unique item!
                        options.append(item)

                if len(next) == 0 and entry not in possible:
                    # This entry has finished decoding. If we _know_ it has
                    # finished decoding, we know that anything after this
                    # entry will not get a chance to decode (ie: early out).
                    have_new_success = True
                    successful.append(entry)

        offset += length

    # Unable to differentiate any more; give one more result with all
    # of the current possible option.
    yield offset, 0, {}, [entry for entry, option in options], successful, possible

class _Cache:
    """ Class to cache differentiated entries. """
    def __init__(self, entries):
        self._cache = []
        self._items = _differentiate(entries)

    def __iter__(self):
        for item in self._cache:
            yield item

        for offset, length, lookup, undistinguished, successful, possible in self._items:
            item = (offset, length, lookup.copy(), undistinguished[:], successful[:], possible[:])
            self._cache.append(item)
            yield item


class Chooser:
    def __init__(self, entries):
        self._entries = entries
        self._cache = _Cache(entries)

    def choose(self, data):
        options = list(self._entries)
        current_offset = 0
        copy = data.copy()
        for offset, length, lookup, undistinguished, successful, possible in self._cache:
            if len(options) <= 1:
                break

            # Remove data from before the current offset, as we cannot use it
            # to differentiate.
            assert offset >= current_offset
            try:
                copy.pop(offset - current_offset)
            except dt.NotEnoughDataError:
                # We don't have enough data left for this option; reduce
                # the possibles to those that have finished decoding.
                options = [option for option in options if option in set(successful + possible)]
                break
            current_offset = offset

            # Check to see if we have a successful item, and remove any items
            # after that item (as they cannot succeed).
            for i, option in enumerate(options):
                if option in successful:
                    # We found a successful item; no options after this can 
                    # succeed (as they are a lower priority).
                    del options[i+1:]
                    break

            if length:
                try:
                    value = int(copy.pop(length))
                    current_offset += length
                except dt.NotEnoughDataError:
                    # We don't have enough data left for this option; reduce
                    # the possibles to those that have finished decoding.
                    options = [option for option in options if option in set(successful + possible)]
                    break

                if lookup:
                    # We found a range of bits that can be used to distinguish
                    # between the diffent options.
                    filter = successful + possible + undistinguished
                    try:
                        filter += lookup[value]
                    except KeyError:
                        pass
                    options = [option for option in options if option in filter]

        return options
