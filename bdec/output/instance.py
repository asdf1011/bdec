#   Copyright (C) 2010 Henry Ludemann
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

import operator

from bdec.data import Data
from bdec.encode.entry import MissingInstanceError
import bdec.entry as ent
import bdec.field as fld
import bdec.output
import bdec.sequence as seq
import bdec.sequenceof as sof

def escape(name):
    return name.replace(' ', '_')

class _Item(object):
    def __init__(self, value, children):
        self._children = children
        self._value = value

    def __getattr__(self, name):
        try:
            return self._children[name]
        except KeyError:
            raise AttributeError(name)

    def __repr__(self):
        return unicode(self._children)

    def __int__(self):
        if self._value is None:
            raise TypeError
        return int(self._value)

class _DecodedItem:
    """ Class to handle creating python instances from decoded entries """
    def __init__(self, entry):
        self._entry = entry
        self._children = []

    def add_entry(self, name, value):
        self._children.append((name, value))

    def get_value(self, value):
        """
        Create a python object representing the decoded protocol entry.
        """
        # We allready have the decoded values for fields; this function shouldn't
        # be used.
        if isinstance(self._entry, fld.Field):
            return value
        if self._entry is None:
            # For the top level object, return the protocol value (if it
            # exists).
            if not self._children:
                result = None
            else:
                result = self._children[0][1]
        elif isinstance(self._entry, sof.SequenceOf):
            result = list(value for name, value in self._children)
        else:
            if value is not None and not self._children:
                # This item has no visible children, but has a value; treat it
                # as the raw value (eg: a sequence with a value).
                result = value
            else:
                children = dict((escape(name), value) for name, value in self._children)
                result = _Item(value, children)

        return result

def get_instance(items):
    """Convert an iterable list of decode items to a python instance."""
    stack = [_DecodedItem(None)]
    for is_starting, name, entry, data, value in items:
        if is_starting:
            stack.append(_DecodedItem(entry))
        else:
            item = stack.pop()
            if not ent.is_hidden(name):
                stack[-1].add_entry(name, item.get_value(value))

    assert len(stack) == 1
    return stack[0].get_value(None)

def decode(decoder, binary):
    """
    Create a python instance representing the decoded data.
    """
    return get_instance(decoder.decode(binary))

def _get_data(obj, child, i, name):
    if name.endswith(':'):
        raise MissingInstanceError(obj, child)

    try: 
        return getattr(obj, escape(name))
    except (AttributeError, KeyError):
        pass

    try:
        return obj[name]
    except (AttributeError, KeyError, TypeError):
        raise MissingInstanceError(obj, child)

def _get_value(obj, child, i, name):
    result = _get_data(obj, child, i, name)
    if isinstance(child, sof.SequenceOf):
        result = [{child.children[0].name: v} for v in result]
    return result

def encode(protocol, value):
    """
    Encode a python instance to binary data.

    Returns a bdec.data.Data instance.
    """
    return reduce(operator.add, protocol.encode(_get_value, {protocol.name: value}), Data())
