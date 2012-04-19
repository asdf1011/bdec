#   Copyright (C) 2008-2010 Henry Ludemann
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
#  
# This file incorporates work covered by the following copyright and  
# permission notice:  
#  
#   Copyright (c) 2010, PRESENSE Technologies GmbH
#   All rights reserved.
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#       * Redistributions of source code must retain the above copyright
#         notice, this list of conditions and the following disclaimer.
#       * Redistributions in binary form must reproduce the above copyright
#         notice, this list of conditions and the following disclaimer in the
#         documentation and/or other materials provided with the distribution.
#       * Neither the name of the PRESENSE Technologies GmbH nor the
#         names of its contributors may be used to endorse or promote products
#         derived from this software without specific prior written permission.
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#   ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#   WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#   DISCLAIMED. IN NO EVENT SHALL PRESENSE Technologies GmbH BE LIABLE FOR ANY
#   DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
The bdec.entry module defines the core entry class (bdec.entry.Entry) and 
errors (derived from bdec.DecodeError) common to all entry types.
"""

import operator

import bdec
import bdec.data as dt
from bdec.expression import Expression, Constant, UndecodedReferenceError

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

class EncodeError(bdec.DecodeError):
    pass

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
        return "'%s' %s" % (self.entry, self.name)

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
        self._encoder = None

        self.constraints = list(constraints)
        for constraint in self.constraints:
            assert getattr(constraint, 'check') is not None

    def _get_children(self):
        return self._children
    def _set_children(self, children):
        from bdec.spec.references import ReferencedEntry
        items = []
        for child in children:
            if isinstance(child, Child):
                items.append(child)
            else:
                # For convenience in the tests, we allow the children to be
                # assigned an array of Entry instances.
                items.append(Child(child.name, child))
            if isinstance(items[-1].entry, ReferencedEntry):
                items[-1].entry.add_parent(items[-1])
        self._children = list(items)
    children = property(_get_children, _set_children)

    def _validate(self):
        if self._decoder is None:
            from bdec.decode import Decoder
            self._decoder = Decoder(self)

    def decode(self, data, context={}, name=None):
        """ Shortcut to bdec.decode.Decoder(self) """
        self._validate()
        return self._decoder.decode(data, context, name)

    def encode(self, query, value):
        if self._encoder is None:
            from bdec.encode import create_encoder
            self._encoder = create_encoder(self)
        value = self._encoder.get_value(query, value, 0, self.name, {})
        return self._encoder.encode(query, value, 0, {}, self.name)

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
