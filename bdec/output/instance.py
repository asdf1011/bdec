#   Copyright (C) 2010 Henry Ludemann
#   Copyright (C) 2010 PRESENSE Technologies GmbH
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

from bdec.encode.entry import MissingInstanceError
import bdec.entry as ent
import bdec.field as fld
import bdec.output
import bdec.sequence as seq
import bdec.sequenceof as sof

def escape(name):
    return name.replace(' ', '_')

class _Item(object):
    def __init__(self):
        self.children = {}
        self.value = None

    def __getattr__(self, name):
        return self.children[name]

    def __repr__(self):
        return unicode(self.children)

    def __int__(self):
        if not self.value:
            raise TypeError
        return int(self.value)

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
                result = _Item()
                if value is not None:
                    # This object can be convert to an integer
                    result.value = value

                for name, value in self._children:
                    result.children[escape(name)] = value
        return result

def decode(decoder, binary):
    """
    Create a python instance representing the decoded data.
    """
    stack = [_DecodedItem(None)]
    for is_starting, name, entry, data, value in decoder.decode(binary):
        if is_starting:
            stack.append(_DecodedItem(entry))
        else:
            item = stack.pop()
            if not ent.is_hidden(name):
                stack[-1].add_entry(name, item.get_value(value))

    assert len(stack) == 1
    return stack[0].get_value(None)

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
    return reduce(operator.add, protocol.encode(_get_value, {protocol.name: value}))
