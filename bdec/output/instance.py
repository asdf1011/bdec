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

import bdec.entry as ent
import bdec.field as fld
import bdec.output
import bdec.sequenceof as sof

def escape(name):
    return name.replace(' ', '_')

class _Item:
    pass

class _DecodedItem:
    """ Class to handle creating python instances from decoded entries """
    def __init__(self, entry):
        self._entry = entry
        self.children = []

    def add_entry(self, name, value):
        self.children.append((name, value))

    def get_value(self):
        """
        Create a python object representing the decoded protocol entry.
        """
        # We allready have the decoded values for fields; this function shouldn't
        # be used.
        assert not isinstance(self._entry, fld.Field)
        if self._entry is None:
            # For the top level object, return the protocol value (if it
            # exists).
            if not self.children:
                result = None
            else:
                result = self.children[0][1]
        elif isinstance(self._entry, sof.SequenceOf):
            result = list(value for name, value in self.children)
        else:
            result = _Item()
            for name, value in self.children:
                setattr(result, escape(name), value)
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
            if not entry.is_hidden():
                if not isinstance(entry, fld.Field):
                    value = item.get_value()
                stack[-1].add_entry(entry.name, value)

    assert len(stack) == 1
    return stack[0].get_value()

def _get_data(obj,child):
    name = child.name
    if name.endswith(':'):
        raise ent.MissingInstanceError(obj, child)

    name = escape(name)

    try: 
        return getattr(obj, name)
    except AttributeError:
        raise ent.MissingInstanceError(obj, child)

def encode(protocol, value):
    """
    Encode a python instance to binary data.

    Returns an iterator to data objects representing the encoded structure.
    """
    return protocol.encode(_get_data, value)
