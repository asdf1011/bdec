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

import bdec.choice as chc
import bdec.data as dt
import bdec.entry as ent
import bdec.field as fld
import bdec.sequence as seq
from bdec.spec import LoadError, xmlspec
import os.path
from pyparsing import Word, alphanums, Literal, StringEnd, ZeroOrMore,\
    ParseException, OneOrMore

_UNIVERSAL = 0
_APPLICATION = 1
_CONTEXT_SPECIFIC = 2
_PRIVATE = 3

_PRIMITIVE = 0
_CONSTRUCTED = 1

def _field(name, length, value):
    """Create a field with a given name an integer value."""
    expected = dt.Data.from_int_big_endian(value, length)
    return fld.Field(name, length=length, format=fld.Field.INTEGER, expected=expected)

def _create_tag(klass, is_constructed, number):
    value = (klass << 6) | (is_constructed << 5) | number
    return _field('tag:', 8, value)

class _Loader:
    """A class for loading asn1 specifications."""

    def __init__(self):
        # Load the xml spec that we will use for doing the decoding.
        filename = os.path.join(os.path.dirname(__file__), '..', '..', 'specs', 'asn1.ber.xml')
        generic_spec, lookup, self._spec = xmlspec.load(filename)

        # Define the basic asn.1 syntax
        name = Word(alphanums)
        entry = name + 'INTEGER'
        entries = '{' + entry + ZeroOrMore(',' + entry) + '}'
        sequence = Literal('SEQUENCE') + entries
        construct = name + '::=' + sequence
        module = name + 'DEFINITIONS' + '::=' + 'BEGIN' + ZeroOrMore(construct) + 'END'

        # Set actions to be performed for the different parts of the syntax.
        entry.setParseAction(self._create_integer)
        entries.setParseAction(self._get_children)
        sequence.setParseAction(self._create_sequence)
        construct.setParseAction(self._set_name)
        module.setParseAction(self._create_module)

        self._parser = module + StringEnd()
        self._common_entries = {}

    def _common(self, name):
        """Get an entry from the specification.

        Stores it in this decoders 'common' dictionary."""
        try:
            return self._common_entries[name]
        except KeyError:
            entry = self._spec[name]
            self._common_entries[name] = entry
            return entry

    def load(self, text):
        """Load a bdec specification from an asn.1 document."""
        try:
            name, common =  self._parser.parseString(text)[0]
        except ParseException, ex:
            raise LoadError(ex)
        return common[0], {}, self._common_entries

    def _create_constructed(self, name, tag, children):
        """Create a constructed entry.

        Handles entries with both definite and indefinite lengths. """
        # FIXME: Handle extra entries after the expected ones...
        # FIXME: Combine the indefinite & definite sections, and use a
        # conditional after the children to eat the rest of the data,
        # depending on whether they are expected or not. This would mean we
        # don't need to add the children to the common entries...
        self._common_entries[tag.name] = tag
        for child in children:
            if isinstance(child, ent.Child):
                child = child.entry
            if child not in self._common_entries:
                self._common_entries[child.name] = child

        indefinite = seq.Sequence('indefinite',
                [tag, _field('', 8, 0x80)] +
                children +
                [_field('', 16, 0x00)])
        definite = seq.Sequence('definite',
                [tag, self._common('definite length:')] + children)
        return chc.Choice(name, [indefinite, definite])

    def _create_integer(self, s, loc, toks):
        return ent.Child(toks[0], self._common('integer'))

    def _create_sequence(self, s, loc, toks):
        tag = _create_tag(_UNIVERSAL, _CONSTRUCTED, 16)
        return self._create_constructed('', tag, toks[1:])

    def _set_name(self, s, loc, toks):
        entry = toks[2]
        entry.name = toks[0]
        return entry

    def _get_children(self, s, loc, toks):
        children = toks[1:-1:2]
        return children

    def _create_module(self, s, loc, toks):
        return (toks[0], toks[4:-1])


def loads(text, filename=None):
    return _Loader().load(text)

def load(filename):
    data = open(filename, 'r')
    text = data.read()
    data.close()
    return loads(text, filename)


