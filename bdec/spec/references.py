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

from bdec.entry import Entry, Child

class MissingReferenceError(Exception):
    def __init__(self, name):
        self.name = name


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
        self._parent = None

    def resolve(self, entry):
        assert self._parent is not None, 'Missing parent when resolving %s' % self
        assert isinstance(entry, Entry)

        # Replace the child entry in the children list
        for i, child in enumerate(self._parent.children):
            if child.entry is self:
                child.entry = entry
                return
        assert False, 'Failed to find entry %s in %s!' % (entry, self._parent)

    def set_parent(self, parent):
        """Set the parent of this referenced entry.

        parent -- A list of bdec.entry.Child instances. When resolving, this
        list is assumed include self, which will be replaced with the 'correct'
        entry."""
        assert self._parent is None, 'Parent has already been set to %s, '\
                'asked to set to %s' % (self._parent, parent)
        self._parent = parent

    def __repr__(self):
        return "ref name='%s' type='%s'" % (self.name, self.type)


class References:
    """A helper class to handle referenced entries.

    Can be used by the specification classes to simplify references to entries
    that haven't been defined yet. """
    def __init__(self):
        self._unresolved_references = []

    def get_common(self, name, type):
        """Get a named common entry.

        Will return a ReferencedEntry instance, which will be replaced with
        the 'real' common instance when the resolve method is called."""
        name = name or type
        type = type or name
        result = ReferencedEntry(name, type)
        self._unresolved_references.append(result)
        return result

    def resolve(self, common):
        """ Resolve all references that are in the common list.

        Will throw a MissingReferenceError if a referenced entry cannot be
        found.

        common - A list of entry instances, where each entry may be a
            referenced entry. All previously referenced items will be looked
            for in this list."""
        # First we find any references in the common list itself.
        lookup = dict((e.name, e) for e in common if not isinstance(e, ReferencedEntry))
        common_references = [e for e in common if isinstance(e, ReferencedEntry)]
        for ref in common_references:
            try:
                entry = lookup[ref.type]
            except KeyError:
                raise MissingReferenceError(ref.type)
            if isinstance(entry, ReferencedEntry):
                raise NotImplementedError("References to references not fully " \
                        "supported for '%s'; try putting the referenced item " \
                        "'%s' first." % (ref.name, ref.type))
            lookup[ref.name] = entry
            self._unresolved_references.remove(ref)

        # Note the we don't iterate over the unresolved references, as the
        # list can change as we iterate over it (in _get_common_entry).
        while self._unresolved_references:
            reference = self._unresolved_references.pop()
            try:
                entry = lookup[reference.type]
            except KeyError:
                raise MissingReferenceError(reference.type)

            assert isinstance(entry, Entry)
            reference.resolve(entry)
        for entry in lookup.values():
            assert isinstance(entry, Entry)
        return [lookup[c.name] for c in common]
