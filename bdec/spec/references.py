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

from bdec import DecodeError
from bdec.entry import Entry, Child

class MissingReferenceError(Exception):
    def __init__(self, reference):
        self.reference = reference
        self.name = reference.type

    def __str__(self):
        return "Reference to unknown entry '%s'!" % self.name

class DuplicateCommonError(Exception):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "Duplicate common entry '%s'" % (self.name)

class ReferencedEntry:
    """
    A entry to insert into child lists when referencing a common entry.

    Used to 'delay' referencing of decoder entries, for the case where a
    decoder entry has been referenced (but has not yet been defined).
    """
    def __init__(self, name, type):
        """
        Construct a referenced entry.

        name -- The name of the type we should resolve to.
        """
        self.name = name
        self.type = type
        self._parents = set()

    def resolve(self, entry):
        assert isinstance(entry, Entry)
        for parent in self._parents:
            parent.entry = entry

    def add_parent(self, parent):
        """Set the parent of this referenced entry.

        parent -- A bdec.entry.Entry instances. When resolving, this entry's child
        list is assumed include self, which will be replaced with the 'correct'
        entry."""
        assert isinstance(parent, Child)
        self._parents.add(parent)

    def __repr__(self):
        result = "ref name='%s'" % self.name
        if self.name != self.type:
            result += " type='%s'" % self.type
        return result


class References:
    """A helper class to handle referenced entries.

    Can be used by the specification classes to simplify references to entries
    that haven't been defined yet. """
    def __init__(self):
        self._unresolved_references = []
        self._common = []

    def get_common(self, name, type=None):
        """Get a named common entry.

        Will return a ReferencedEntry instance, which will be replaced with
        the 'real' common instance when the resolve method is called."""
        name = name or type
        type = type or name
        result = ReferencedEntry(name, type)
        self._unresolved_references.append(result)
        return result

    def get_names(self):
        return [e.name for e in self._common]

    def add_common(self, entry):
        """Add a common entry that will be resolvable."""
        if entry.name in (e.name for e in self._common):
            raise DuplicateCommonError(entry.name)
        self._common.append(Child(entry.name, entry))

    def resolve_reference(self, ref):
        lookup = dict((e.name, e.entry) for e in self._common if not isinstance(e, ReferencedEntry))
        try:
            entry = lookup[ref.type]
        except KeyError:
            raise MissingReferenceError(ref)
        if isinstance(entry, ReferencedEntry):
            raise NotImplementedError("References to references not fully " \
                    "supported for '%s'; try putting the referenced item " \
                    "'%s' first." % (ref.name, ref.type))
        return entry

    def resolve(self):
        """ Resolve all references that are in the common list.

        Will throw a MissingReferenceError if a referenced entry cannot be
        found.

        return -- A list of the resolved common entries."""
        # First we find any references in the common list itself.
        common_references = [c for c in self._common if isinstance(c.entry, ReferencedEntry)]
        for c in common_references:
            entry = self.resolve_reference(c.entry)
            c.entry.resolve(entry)
            i = self._common.index(c)
            self._common.pop(i)
            self._common.insert(i, Child(c.entry.name, entry))
            self._unresolved_references.remove(c.entry)

        # Note the we don't iterate over the unresolved references, as the
        # list can change as we iterate over it (in _get_common_entry).
        lookup = dict((e.name, e.entry) for e in self._common if not isinstance(e, ReferencedEntry))
        while self._unresolved_references:
            reference = self._unresolved_references.pop()
            try:
                entry = lookup[reference.type]
            except KeyError:
                raise MissingReferenceError(reference)

            assert isinstance(entry, Entry)
            reference.resolve(entry)
        for entry in lookup.values():
            assert isinstance(entry, Entry)
        return [lookup[c.name] for c in self._common]
