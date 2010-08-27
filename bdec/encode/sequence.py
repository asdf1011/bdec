#   Copyright (C) 2008-2009 Henry Ludemann
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

from collections import defaultdict
import operator

from bdec import DecodeError
from bdec.constraints import Equals
from bdec.data import Data
from bdec.encode.entry import EntryEncoder, MockSequenceValue
from bdec.expression import UndecodedReferenceError
from bdec.inspect.solver import solve
from bdec.inspect.type import EntryValueType, EntryLengthType

class CyclicEncodingError(DecodeError):
    def __init__(self, entry, loop):
        DecodeError.__init__(self, entry)
        self._loop = loop

    def __str__(self):
        return 'Unable to encode %s; cyclic dependency detected. There is a ' \
                'loop between %s. Sorry, this is a current implementation ' \
                'limitation. Entries referenced in a len{XXX} must be encoded ' \
                'before entries that use it, so the length is known. Likewise, ' \
                'hidden entries whose value is referenced (eg: ${XXX}) must ' \
                'be encoded after the entry that uses it, so the value can ' \
                'be deduced from the place where it is used. Try separating ' \
                'the entry referenced in the len{XXX} from that referenced ' \
                'in the ${XXX}, or alternatively make the entry visible.' % \
                (self.entry, ' -> '.join("'%s'" % e.name for e in self._loop))


class MissingValueError(DecodeError):
    def __str__(self):
        return 'Unable to solve value for %s as value is missing. This is an ' \
                'encoder bug; sorry.' % self.entry


def _detect_dependencies(children, is_hidden):
    """Detect dependencies between the child entries.

    Returns a dict mapping (child: [child, child]) where the key child can
    only be decoded after the value children."""
    dependencies = defaultdict(list)
    for child in children:
        for output in child.params:
            if output.direction == output.OUT:
                name = output.name.split('.')[0]
                if name != child.name:
                    # We have an output for another child; find out who it
                    # is, and add a dependancy on it.
                    for other in children:
                        if other.name == name:
                            dependencies[other].append(child)
                        else:
                            # Find all other parameters using this child
                            for input in other.params:
                                if input.direction == input.IN:
                                    if output.name == input.name:
                                        dependencies[other].append(child)
    return dependencies

def _populate_dependencies(entry, child, dependencies, visited=None, chain=None):
    if visited is None:
        visited = set()
    if chain is None:
        chain = list()
    if child in chain:
        raise CyclicEncodingError(entry, chain + [child])
    visited.add(child)
    chain.append(child)
    for dependency in dependencies[child]:
        _populate_dependencies(entry, dependency, dependencies, visited, chain[:])
    return visited

def _encoding_order(encoder, is_hidden):
    """Returns a list of children in the order they should be encoded."""
    direct_dependencies = _detect_dependencies(encoder.children, is_hidden)
    dependencies = {}
    for child in encoder.children:
        dependencies[child] = _populate_dependencies(encoder.entry, child,
                direct_dependencies)
        # The algorithm adds the child as a dependency of itself; this is a
        # little ugly in debugging output, so we remove it.
        dependencies[child].remove(child)
    result = list(encoder.children)
    for child in encoder.children:
        if dependencies[child]:
            current_offset = result.index(child)
            new_offset = max(result.index(c) for c in dependencies[child])
            if new_offset > current_offset:
                # We have to shift this item; it has to be encoded later than
                # it currently is.
                old = result.pop(current_offset)
                result.insert(new_offset, child)
    return result


class SequenceEncoder(EntryEncoder):
    def __init__(self, *args, **kwargs):
        EntryEncoder.__init__(self, *args, **kwargs)
        self._order = None

    def order(self):
        if self._order is None:
            # We perform dependency analysis on the child parameters to determine
            # the order in which the child entries should be encoded. For example,
            # we can't encode a hidden field that is referenced elsewhere without
            # first encoding the location where it is referenced to try and
            # determine the value of the hidden field.
            self._order = _encoding_order(self, self.is_hidden)
        return self._order

    def _is_unknown_value(self, value):
        if value in [None, '', MockSequenceValue()]:
            return True
        try:
            int(value)
            return False
        except Exception:
            return True

    def _fixup_value(self, value, context):
        """
        Allow entries to modify the value to be encoded.
        """
        if self.entry.value and self._is_unknown_value(value):
            try:
                # Get the value from the expression
                return self.entry.value.evaluate(context)
            except UndecodedReferenceError:
                pass

            # This could be a hidden entry; get the expected value from the
            # constraints
            for constraint in self.entry.constraints:
                if isinstance(constraint, Equals):
                    return constraint.limit.evaluate(context)
        return value

    def _encode(self, query, value, context):
        if self.entry.value:
            # Update the context with the detected parameters
            if value is None:
                raise MissingValueError(self.entry)
            self._solve(self.entry.value, int(value), context)

        sequence_data = {}
        for child in self.order():
            data = reduce(operator.add, self._encode_child(child, query, value, 0, context), Data())
            sequence_data[child] = data
        for child in self.children:
            yield sequence_data[child]

