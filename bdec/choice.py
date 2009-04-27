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


import bdec.data as dt
import bdec.entry

class Choice(bdec.entry.Entry):
    """
    An entry that can be one of many entries.

    The first entry to decode correctly will be used.
    """

    def __init__(self, name, children, length=None):
        bdec.entry.Entry.__init__(self, name, length, children)

        assert len(children) > 0
        self._chooser = None

    def _get_context(self, query, parent):
        try:
            return query(parent, self)
        except bdec.entry.MissingInstanceError:
            # Choice entries can be completely hidden
            return parent

    def _decode(self, data, context, name):
        if self._chooser is None:
            import bdec.inspect.chooser as chsr
            self._chooser = chsr.Chooser([child.entry for child in self.children])
        # Convert the list of entries to a list of children.
        possibles = []
        for entry in self._chooser.choose(data):
            for child in self.children:
                if child.entry is entry:
                    possibles.append(child)
                    break
            else:
                raise Exception('Failed to find child from possible option %s!' % entry)

        yield (True, name, self, data, None)

        failure_expected = False
        if len(possibles) == 0:
            # None of the items match. In this case we want to choose
            # the 'best' failing option, so we'll examine all of the
            # children.
            possibles = self.children
            failure_expected = True

        if len(possibles) == 1:
            best_guess = possibles[0]
        else:
            # We have multiple possibilities. We'll decode them one
            # at a time until one of them succeeds; if none decode,
            # we'll re-raise the exception of the 'best guess'.
            #
            # Note: If we get in here, at best we'll decode the successfully
            # decoding item twice. This can have severe performance
            # implications if choices are embedded within choices (as
            # we get O(N^2) runtime cost).
            #
            # We should possibly emit a warning if we get in here (as it
            # indicates that the specification could be better written).
            best_guess = None
            best_guess_bits = 0
            for child in possibles:
                try:
                    bits_decoded = 0
                    for is_starting, child_name, entry, entry_data, value in self._decode_child(child, data.copy(), context.copy()):
                        if not is_starting:
                            bits_decoded += len(entry_data)

                    # We successfully decoded the entry!
                    best_guess = child
                    break
                except bdec.DecodeError:
                    if best_guess is None or bits_decoded > best_guess_bits:
                        best_guess = child
                        best_guess_bits = bits_decoded

        # Decode the best option.
        for is_starting, child_name, entry, data, value in self._decode_child(best_guess, data, context):
            yield is_starting, child_name, entry, data, value

        assert not failure_expected
        yield (False, name, self, dt.Data(), None)

    def _encode(self, query, value):
        # We attempt to encode all of the embedded items, until we find
        # an encoder capable of doing it.
        best_guess = None
        best_guess_bits = 0
        for child in self.children:
            try:
                bits_encoded = 0
                child_value = child.entry.get_context(query, value)
                for data in child.entry.encode(query, child_value):
                    bits_encoded += len(data)

                # We successfully encoded the entry!
                best_guess = child
                break
            except bdec.DecodeError:
                if best_guess is None or bits_encoded > best_guess_bits:
                    best_guess = child
                    best_guess_bits = bits_encoded

        child_value = best_guess.entry.get_context(query, value)
        return best_guess.entry.encode(query, child_value)

    def _range(self, ignore_entries):
        minimum = min(child.entry.range(ignore_entries).min for child in self.children)
        maximum = max(child.entry.range(ignore_entries).max for child in self.children)
        return bdec.entry.Range(minimum, maximum)
