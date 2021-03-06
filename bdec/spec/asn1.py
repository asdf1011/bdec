#   Copyright (C) 2010-2012 Henry Ludemann
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

import bdec.choice as chc
from bdec.constraints import Equals, Minimum, Maximum
import bdec.data as dt
import bdec.entry as ent
import bdec.expression as expr
import bdec.field as fld
import bdec.sequence as seq
from bdec.spec import LoadError, xmlspec
from bdec.spec.ebnf import parse
from bdec.spec.references import ReferencedEntry
import operator
import os.path
from pyparsing import Word, nums, alphanums, StringEnd, \
    ParseException, Optional, Combine, oneOf, alphas,\
    QuotedString, empty, lineno, SkipTo, ParserElement

ParserElement.enablePackrat()

class Asn1Error(LoadError):
    def __init__(self, filename, lineno):
        self.filename = filename
        self.lineno = lineno

    def location(self):
        return '%s[%i]' % (self.filename, self.lineno)

    def __str__(self):
        return '%s: Unknown error' % self.location()


class Asn1ParseError(Asn1Error):
    def __init__(self, message, filename, lineno):
        Asn1Error.__init__(self, filename, lineno)
        self.message = message

    def __str__(self):
        return '%s: %s' % (self.location(), self.message)


class NotImplementedError(Asn1Error):
    def __init__(self, name, tokens, filename, lineno):
        Asn1Error.__init__(self, filename, lineno)
        self.name = name
        self.tokens = tokens

    def __str__(self):
        return "%s: Type '%s' is not implemented (%s)." % (self.location(), self.name, self.tokens)

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

def _parse_number(s, l, t):
    return int(t[0])

class _Loader:
    """A class for loading asn1 specifications."""

    def __init__(self, filename, references):
        self._references = references
        self._parser, parsers, self._source_lookup = self._load_ebnf()

        # Default for all handlers will be to fail on 'not implemented'. We
        # then have to manually go through and enable all handlers explicitly.
        self.filename = filename
        def not_implemented_handler(name):
            def _handler(text, location, tokens):
                raise NotImplementedError(name, tokens, filename, lineno(location, text))
            return _handler
        for name, entry in parsers.items():
            entry.setParseAction(not_implemented_handler(name))
        self._common_entries = {}
        self._constants = {}

        # Default handler to pass the childrens tokens from a parser element.
        pass_children = lambda t, l, tokens: tokens
        def entries(name):
            """Add a parser handler for name that will only allow bdec entries.

            Attempting to return any other type of token will result in a
            NotImplementedError."""
            def allow_entries_with_name(t, l, tokens):
                for entry in tokens:
                    if not isinstance(entry, ent.Child) and not isinstance(entry, ent.Entry):
                        raise NotImplementedError(name, tokens, filename, lineno(l, t))
                return tokens
            parsers[name].setParseAction(allow_entries_with_name)

        parsers['ModuleDefinition'].setParseAction(self._create_module)
        parsers['DefinitiveIdentifier'].setParseAction(lambda s,l,t:t[1:-1])
        parsers['ModuleIdentifier'].setParseAction(pass_children)
        parsers['TagDefault'].setParseAction(self._accept_empty)
        parsers['ExtensionDefault'].setParseAction(self._accept_empty)
        parsers['Exports'].setParseAction(self._accept_empty)
        parsers['Imports'].setParseAction(self._accept_empty)
        parsers['AssignmentList'].setParseAction(pass_children)
        parsers['IntegerType'].setParseAction(self._create_integer)
        parsers['BuiltinType'].setParseAction(pass_children)
        parsers['Type'].setParseAction(pass_children)
        parsers['RawType'].setParseAction(pass_children)
        parsers['NamedType'].setParseAction(self._set_entry_name)
        entries('ComponentType')
        parsers['ComponentTypeList'].setParseAction(lambda s,l,t:t[0::2])
        entries('RootComponentTypeList')
        entries('ComponentTypeLists')
        parsers['SequenceType'].setParseAction(self._create_sequence)
        parsers['TypeAssignment'].setParseAction(self._set_type_name)
        entries('Assignment')
        entries('ModuleBody')
        parsers['SignedNumber'].setParseAction(self._parse_integer)
        parsers['BooleanType'].setParseAction(self._create_boolean)
        parsers['NamedNumberList'].setParseAction(self._create_named_numeric_list)

        # Ignore the object identifiers. What should we do with these?
        parsers['NameForm'].setParseAction(lambda s,l,t:[])
        parsers['DefinitiveObjIdComponent'].setParseAction(lambda s,l,t:[])
        parsers['DefinitiveObjIdComponentList'].setParseAction(lambda s,l,t:[])
        parsers['DefinitiveNumberForm'].setParseAction(lambda s,l,t:[])
        parsers['DefinitiveNameAndNumberForm'].setParseAction(lambda s,l,t:[])

        # Enumeration entries.
        parsers['NamedNumber'].setParseAction(lambda s, l, t: {'name': t[0], 'value': t[2]})
        parsers['EnumerationItem'].setParseAction(pass_children)
        parsers['Enumeration'].setParseAction(lambda s, l, t: {'items':t[::2]})
        parsers['RootEnumeration'].setParseAction(pass_children)
        parsers['Enumerations'].setParseAction(self._create_enumeration)
        parsers['EnumeratedType'].setParseAction(lambda s, l, t: t[2])
        parsers['ExceptionSpec'].setParseAction(self._accept_empty)

        # Choice entries
        parsers['AlternativeTypeList'].setParseAction(lambda s,l,t:t[0::2])
        entries('RootAlternativeTypeList')
        entries('AlternativeTypeLists')
        parsers['ChoiceType'].setParseAction(self._create_choice)

        # Value references
        parsers['valuereference'].setParseAction(lambda s,l,t:t[0])
        parsers['EnumeratedValue'].setParseAction(self._create_enumerated_value)
        parsers['BuiltinValue'].setParseAction(lambda s,l,t:t[0])
        parsers['Value'].setParseAction(lambda s,l,t:t[0])
        parsers['ValueAssignment'].setParseAction(self._set_constant)

        # Constraints
        parsers['LowerEndValue'].setParseAction(self._lower_constraint)
        parsers['LowerEndpoint'].setParseAction(pass_children)
        parsers['UpperEndValue'].setParseAction(self._upper_constraint)
        parsers['UpperEndpoint'].setParseAction(pass_children)
        parsers['ValueRange'].setParseAction(lambda s,l,t:[t[0], t[2]])
        parsers['Constraint'].setParseAction(lambda s,l,t:t[1:-1])
        parsers['ConstrainedType'].setParseAction(self._create_constrained_type)

        parsers['SubtypeElements'].setParseAction(pass_children)
        parsers['Elements'].setParseAction(pass_children)
        parsers['IntersectionElements'].setParseAction(pass_children)
        parsers['Intersections'].setParseAction(pass_children)
        parsers['Unions'].setParseAction(pass_children)
        parsers['ElementSetSpec'].setParseAction(pass_children)
        parsers['RootElementSetSpec'].setParseAction(pass_children)
        parsers['ElementSetSpecs'].setParseAction(pass_children)
        parsers['SubtypeConstraint'].setParseAction(pass_children)
        parsers['ConstraintSpec'].setParseAction(pass_children)

    def _load_ebnf(self):
        # Load the xml spec that we will use for doing the decoding.
        asn1_filename = os.path.join(os.path.dirname(__file__), '..', '..', 'specs', 'asn1.ber.xml')
        generic_spec, lookup = xmlspec.load(asn1_filename, file(asn1_filename, 'r'), self._references)

        table = {
                'bstring' : Combine("'" + Word('01') + "'B"),
                'xmlbstring' : Word('01'),
                'hstring' : Combine("'" + Word('abcdef' + nums) + "'H"),
                'xmlhstring' : Word('abcdef' + nums),
                'number' : Word(nums),
                'typereference' : Word(alphanums + '-'),
                'modulereference' : Word(alphanums + '-'),
                'realnumber' : Combine(Word(nums) + Optional('.' + Word(nums)) + Optional(oneOf('eE') + Word(nums))),
                'empty' : empty,
                #'identifier' : Combine(oneOf(alphas) + Optional(Word(alphanums + '-'))),
                'identifier' : Word(alphanums + '-'),
                'cstring' : QuotedString('"', escChar='"'),
                'xmlcstring' : empty, # FIXME
                }
        table['number'].setParseAction(_parse_number)

        # Load the ebnf for the ASN.1 format, so we know how to parse the specification.
        parsers = parse(open('bdec/spec/asn1.ebnf', 'r').read(), table)
        parser = parsers['ModuleDefinition'] + StringEnd()
        parser.ignore('--' + SkipTo('\n'))

        return parser, dict((name, entry) for name, entry in parsers.items() if name not in table), lookup

    def _create_named_numeric_list(self, s, l, t):
        value = 0
        options = []
        for token in t[0::2]:
            name = token['name']
            value = int(token['value'])
            options.append(seq.Sequence(name,
                [ent.Child('value:', self._common('integer'))],
                value=expr.ValueResult('value:'), constraints=[Equals(value)]))
            value += 1
        return chc.Choice('named numeric list', options)

    def _create_enumeration(self, s, l, t):
        value = 0
        options = []
        for token in t[0]['items']:
            if not isinstance(token, basestring):
                name = token['name']
                value = int(token['value'])
            else:
                name = token
            options.append(seq.Sequence(name,
                [ent.Child('value:', self._common('enumerated'))],
                value=expr.ValueResult('value:'), constraints=[Equals(value)]))
            value += 1
        if len(t) > 1:
            # We have an exception spec in this item!
            options.append(ent.Child('unknown:', self._common('enumerated')))
        return chc.Choice('enumeration', options)

    def _create_enumerated_value(self, s, l, t):
        assert len(t) == 1
        try:
            return int(t[0])
        except ValueError:
            try:
                return self._constants[t[0]]
            except KeyError:
                raise Exception('Unknown constraint', t[0])

    def _set_constant(self, s, l, t):
        self._constants[t[0]] = t[3]
        return []

    def _lower_constraint(self, s, l, t):
        if t[0] == 'MIN':
            return []
        return Minimum(int(t[0]))

    def _upper_constraint(self, s, l, t):
        if t[0] == 'MAX':
            return []
        return Maximum(int(t[0]))

    def _create_constrained_type(self, s, l, t):
        if isinstance(t[0].entry, ReferencedEntry):
            name = t[0].name
            if not name.endswith(':'):
                name += ':'
            result = seq.Sequence(t[0].name, [ent.Child(name, t[0].entry)],
                    value=expr.ValueResult(name), constraints=t[1:])
            t[0].entry.add_parent(result.children[0])
            return [result]
        del t[0].constraints
        t[0].constraints = t[1:]
        return [t[0]]

    def _parse_integer(self, s, l, t):
        if len(t) == 1:
            return t[0]
        assert len(t) == 2
        return -t[0]

    def _accept_empty(self, t, l, tokens):
        # We only currently handle empty tags
        if tokens:
            raise NotImplementedError('empty', tokens, self.filename, lineno(l, t))

    def _common(self, name):
        """Get a common entry from the specification."""
        return self._references.get_common(name)

    def load(self, text):
        """Load a bdec specification from an asn.1 document."""
        try:
            name, modules =  self._parser.parseString(text)[0]
        except ParseException, ex:
            raise Asn1ParseError(ex, self.filename, ex.lineno)
        common = dict((entry.name, entry) for entry in modules)
        common.update(self._common_entries)
        for module in common.values():
            self._references.add_common(module)
        return modules[0], self._source_lookup

    def _create_constructed(self, name, tag, children):
        """Create a constructed entry.

        Handles entries with both definite and indefinite lengths. """
        # Constructed entries can be either indefinite (no specified length,
        # but terminated with a null), or definite (with a specified length).
        #
        # The 'header:' is split into two to avoid cyclic dependancies while
        # encoding;
        # * 'footer:' depends on 'header:' for the type
        # * 'header:' depends on 'footer:' for the length
        # By moving the length out of 'header:', we work around this
        # dependancy.
        #
        # PROBLEM: By splitting the dependancy in this way, we lose the
        # ability to put 'definite' first, as we no longer have a field
        # present to choose on. A better solution is to properly solve
        # dependencies between 'header:' and 'footer:'.
        header = chc.Choice('header:', [
            seq.Sequence('indefinite', [
                seq.Sequence('type', [], value=expr.Constant(1)),
                _field('', 8, 0x80),
                ]),
            seq.Sequence('definite', [
                seq.Sequence('type', [], value=expr.Constant(0)),
                ])
            ])
        header_length = chc.Choice('header length:', [
            seq.Sequence('indefinite', [
                    seq.Sequence('type', [],
                        value=expr.ValueResult('header:.type'),
                        constraints=[Equals(expr.Constant(1))])],
                value=expr.Constant(0)),
            seq.Sequence('definite', [
                    seq.Sequence('type', [],
                        value=expr.ValueResult('header:.type'),
                        constraints=[Equals(expr.Constant(0))]),
                    self._common('definite length:')],
                value=expr.ValueResult('definite length:')),
            ])

        # FIXME: Handle extra entries after the expected ones...
        footer = chc.Choice('footer:', [
                    seq.Sequence('indefinite', [_field('', 16, 0x00)],
                        value=expr.ValueResult('header:.type'),
                        constraints=[Equals(expr.Constant(1))]),
                    seq.Sequence('definite', [
                            seq.Sequence('definite length:', [],
                                value=reduce(operator.add, (expr.LengthResult(c.name) for c in children)),
                                constraints=[Equals(expr.ValueResult('header length:') * expr.Constant(8))])
                            ],
                        value=expr.ValueResult('header:.type'),
                        constraints=[Equals(expr.Constant(0))]),
                    ])
        return seq.Sequence(name, [tag, header, header_length] + children + [footer])

    def _set_entry_name(self, s, loc, toks):
        toks[1].name = toks[0]
        return toks[1]

    def _set_type_name(self, s, loc, toks):
        toks[2].name = toks[0]
        self._common_entries[toks[2].name] = toks[2]
        return toks[2]

    def _create_integer(self, s, loc, toks):
        if len(toks) == 1:
            return ent.Child('integer', self._common('integer'))

        # This is an integer with a range of values (ie: an enumeration).
        return chc.Choice('values', toks[2:-1])

    def _create_boolean(self, s, loc, toks):
        return ent.Child(toks[0], self._common('boolean'))

    def _create_sequence(self, s, loc, toks):
        tag = _create_tag(_UNIVERSAL, _CONSTRUCTED, 16)
        return self._create_constructed('sequence', tag, toks[2:-1])

    def _create_choice(self, s, loc, toks):
        return chc.Choice('choice', toks[2:-1])

    def _create_module(self, s, loc, toks):
        return toks[0], toks[4:-1]


def loads(text, filename, references):
    return _Loader(filename, references).load(text)

def load(filename, specfile, references):
    text = specfile.read()
    return loads(text, filename, references)

