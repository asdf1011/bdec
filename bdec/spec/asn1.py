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
from bdec.constraints import Equals
import bdec.data as dt
import bdec.entry as ent
import bdec.expression as expr
import bdec.field as fld
import bdec.sequence as seq
from bdec.spec import LoadError, xmlspec
import os.path
from pyparsing import Word, nums, alphanums, Literal, StringEnd, ZeroOrMore,\
    ParseException, OneOrMore, Optional, Forward

_UNIVERSAL = 0
_APPLICATION = 1
_CONTEXT_SPECIFIC = 2
_PRIVATE = 3

_PRIMITIVE = 0
_CONSTRUCTED = 1

def _field(name, length, value):
    """Create a field with a given name an integer value."""
    return fld.Field(name, length=length, format=fld.Field.INTEGER, constraints=[Equals(value)])

def _create_tag(klass, is_constructed, number):
    value = (klass << 6) | (is_constructed << 5) | number
    return _field('tag:', 8, value)

class _Loader:
    """A class for loading asn1 specifications."""

    def __init__(self):
        # Load the xml spec that we will use for doing the decoding.
        filename = os.path.join(os.path.dirname(__file__), '..', '..', 'specs', 'asn1.ber.xml')
        generic_spec, self._spec, lookup = xmlspec.load(filename)

        # Define the basic asn.1 syntax
        entry = Forward()
        name = Word(alphanums)
        named_value = name + '(' + Word(nums) + ')'
        named_entry = name + entry
        entries = '{' + named_entry + ZeroOrMore(',' + named_entry) + '}'

        integer = 'INTEGER' + Optional('{' + named_value + ZeroOrMore(',' + named_value) + '}')
        boolean = Literal('BOOLEAN')
        sequence = 'SEQUENCE' + entries
        choice = 'CHOICE' + entries

        entry << (integer | boolean | sequence | choice)

        construct = name + '::=' + entry
        module = name + 'DEFINITIONS' + '::=' + 'BEGIN' + OneOrMore(construct) + 'END'

        # Set actions to be performed for the different parts of the syntax.
        named_value.setParseAction(self._create_named_value)
        named_entry.setParseAction(self._set_entry_name)
        integer.setParseAction(self._create_integer)
        boolean.setParseAction(self._create_boolean)
        entries.setParseAction(self._get_children)
        sequence.setParseAction(self._create_sequence)
        choice.setParseAction(self._create_choice)
        construct.setParseAction(self._set_name)
        module.setParseAction(self._create_module)

        self._parser = module + StringEnd()
        self._common_entries = {}

    def _add_common(self, entry):
        """Add all specification common entries to 'our' common list."""
        if entry.name not in self._common_entries:
            if entry.name in self._spec:
                self._common_entries[entry.name] = entry
            for child in entry.children:
                self._add_common(child.entry)

    def _common(self, name):
        """Get a common entry from the specification.

        Stores it in this decoder's 'common' dictionary."""
        try:
            return self._common_entries[name]
        except KeyError:
            entry = self._spec[name]
            self._add_common(entry)
            return entry

    def load(self, text):
        """Load a bdec specification from an asn.1 document."""
        try:
            name, common =  self._parser.parseString(text)[0]
        except ParseException, ex:
            raise LoadError(ex)
        return common[0], self._common_entries, {}

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

    def _set_entry_name(self, s, loc, toks):
        toks[1].name = toks[0]
        return toks[1]

    def _create_named_value(self, s, loc, toks):
        name = toks[0]
        value = int(toks[2])
        return fld.Field(name, format=fld.Field.INTEGER, length=8, constraints=[Equals(value)])

    def _create_integer(self, s, loc, toks):
        if len(toks) == 1:
            return ent.Child('integer', self._common('integer'))

        # This is an integer with a range of values.
        values = toks[2:-1:2]
        choice = chc.Choice('integer range:', values)
        tag = _create_tag(_UNIVERSAL, _PRIMITIVE, 2)
        return seq.Sequence('integer', [tag, choice])

    def _create_boolean(self, s, loc, toks):
        return ent.Child(toks[0], self._common('boolean'))

    def _create_sequence(self, s, loc, toks):
        tag = _create_tag(_UNIVERSAL, _CONSTRUCTED, 16)
        return self._create_constructed('sequence', tag, toks[1:])

    def _create_choice(self, s, loc, toks):
        return chc.Choice('choice', toks[1:])

    def _set_name(self, s, loc, toks):
        entry = toks[2]
        name = toks[0]
        if isinstance(entry, chc.Choice):
            for child in entry.children:
                child.name = name
        else:
            entry.name = name
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


