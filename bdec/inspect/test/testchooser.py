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


import unittest

import bdec.choice as chc
from bdec.constraints import Equals, Minimum, Maximum
import bdec.data as dt
import bdec.expression as expr
import bdec.field as fld
import bdec.inspect.chooser as chsr
import bdec.sequence as seq

class TestProtocolStream(unittest.TestCase):
    def test_field(self):
        a = fld.Field('a', 8)
        stream = chsr._ProtocolStream(a)
        self.assertEqual(a, stream.entry)
        self.assertEqual([], stream.next())

    def test_sequence(self):
        blah = seq.Sequence('blah', [fld.Field('a', 8), fld.Field('b', 8)])
        stream = chsr._ProtocolStream(blah)
        self.assertEqual(0, len(stream.data))

        # Now we should move to 'a'
        next = stream.next()
        self.assertEqual(1, len(next))
        self.assertEqual('a', next[0].entry.name)

        # Now we should move to 'b'
        next = next[0].next()
        self.assertEqual(1, len(next))
        self.assertEqual('b', next[0].entry.name)

        # And then we should be done.
        self.assertEqual(0, len(next[0].next()))

    def test_choice(self):
        blah = chc.Choice('blah', [fld.Field('a', 8), fld.Field('b', 8)])
        stream = chsr._ProtocolStream(blah)
        self.assertEqual(0, len(stream.data))

        # Now we should move to 'a' or 'b'
        next = stream.next()
        self.assertEqual(2, len(next))
        self.assertEqual('a', next[0].entry.name)

        # Now both options should finish
        self.assertEqual(0, len(next[0].next()))
        self.assertEqual(0, len(next[1].next()))


class TestChooser(unittest.TestCase):
    def test_select_single_entry(self):
        chooser = chsr.Chooser([fld.Field("blah", 8)])
        result = chooser.choose(dt.Data("a"))
        self.assertEqual(1, len(result))

    def test_matching_sequence(self):
        a = seq.Sequence("a", [
            fld.Field("unknown a", 8),
            fld.Field("blah", 8, constraints=[Equals(dt.Data('y'))])])
        b = seq.Sequence("b", [
            fld.Field("blah", 8, constraints=[Equals(dt.Data('z'))]),
            fld.Field("unknown b", 8)])
        chooser = chsr.Chooser([a, b])
        self.assertEqual([b], chooser.choose(dt.Data("za")))
        # Note that 'b' shouldn't be possible, as 'a' must be successful
        self.assertEqual([a], chooser.choose(dt.Data("zy")))
        self.assertEqual([a], chooser.choose(dt.Data("ky")))

    def test_short_matches_work(self):
        # There was a bug with where an option wouldn't be matched if a longer
        # option matched past the end of the shorter option.
        a = fld.Field("a", 16, constraints=[Equals(dt.Data("yz"))])
        b = fld.Field("b", 8)
        chooser = chsr.Chooser([a, b])
        self.assertEqual([b], chooser.choose(dt.Data("xa")))
        self.assertEqual([a, b], chooser.choose(dt.Data("yz")))
        # FIXME: We currently don't distinguish based on the amount of data
        # available.
        #self.assertEqual([b], chooser.choose(dt.Data("y")))

    def test_choose_within_choice(self):
        a = chc.Choice('a', [
            fld.Field('a1', 8, constraints=[Equals(dt.Data('a'))]),
            fld.Field('a2', 8, constraints=[Equals(dt.Data('A'))])])
        b = chc.Choice('b', [
            fld.Field('b1', 8, constraints=[Equals(dt.Data('b'))]),
            fld.Field('b2', 8, constraints=[Equals(dt.Data('B'))])])
        chooser = chsr.Chooser([a, b])
        self.assertEqual([a], chooser.choose(dt.Data("a")))
        self.assertEqual([a], chooser.choose(dt.Data("A")))
        self.assertEqual([b], chooser.choose(dt.Data("b")))
        self.assertEqual([b], chooser.choose(dt.Data("B")))

    def test_differentiate_after_choice(self):
        # We need to differentiate after a choice option; for example, there
        # may be a common enumerated header field, then the distinguishing
        # message identifier.
        initial = fld.Field('d', 8)
        common_choice = chc.Choice('common', [fld.Field('c1', 8), fld.Field('c2', 8)])
        a = seq.Sequence("a", [
            initial,
            common_choice,
            fld.Field('a', 8, constraints=[Equals(dt.Data('a'))])])
        b = seq.Sequence("b", [
            initial,
            common_choice,
            fld.Field('b', 8, constraints=[Equals(dt.Data('b'))])])

        chooser = chsr.Chooser([a, b])
        self.assertEqual([a], chooser.choose(dt.Data("xya")))
        self.assertEqual([b], chooser.choose(dt.Data("xyb")))
        self.assertEqual([], chooser.choose(dt.Data("xyc")))

    def test_choice_in_choice(self):
        alpha = chc.Choice('alpha', [
            fld.Field('a', 8, constraints=[Equals(dt.Data('a'))]),
            fld.Field('b', 8, constraints=[Equals(dt.Data('b'))])])
        num = chc.Choice('num', [
            fld.Field('1', 8, constraints=[Equals(dt.Data('1'))]),
            fld.Field('2', 8, constraints=[Equals(dt.Data('2'))])])
        alphanum = chc.Choice('alphanum', [alpha, num])
        other = fld.Field('other', 8)
        chooser = chsr.Chooser([alphanum, other])
        self.assertEqual([alphanum], chooser.choose(dt.Data("1")))
        self.assertEqual([alphanum], chooser.choose(dt.Data("a")))
        self.assertEqual([other], chooser.choose(dt.Data("%")))

    def test_min_max_differentiation(self):
        # Some entries have a valid range of values, and so it is convenient
        # to offer them as a choice of fields with a min and max value (eg:
        # for pdf 'names' only certain characters are valid). It would be
        # good to differentiate on these.
        a = fld.Field("a", 8, constraints=[Minimum(0x10), Maximum(0x20)])
        b = fld.Field("b", 8, constraints=[Minimum(0x25), Maximum(0x35)])
        chooser = chsr.Chooser([a, b])
        self.assertEqual([], chooser.choose(dt.Data("\x0f")))
        self.assertEqual([a], chooser.choose(dt.Data("\x10")))
        self.assertEqual([a], chooser.choose(dt.Data("\x20")))
        self.assertEqual([], chooser.choose(dt.Data("\x21")))
        self.assertEqual([b], chooser.choose(dt.Data("\x25")))

    def test_ignores_later_options_when_option_fully_decodes(self):
        # If we get an option that we believe fully decodes, don't list any items
        # lower in the priority chain as potentials.
        a = fld.Field("a", 8, constraints=[Equals(dt.Data('\x00'))])
        b = fld.Field("b", 8)
        chooser = chsr.Chooser([a, b])
        self.assertEqual([a], chooser.choose(dt.Data("\x00")))
        self.assertEqual([b], chooser.choose(dt.Data("\x01")))

    def test_only_valid_sizes_selected(self):
        a = fld.Field("a", 24)
        b = fld.Field("b", 8)
        c = fld.Field("c", 32)
        d = fld.Field("d", 16)
        chooser = chsr.Chooser([a, b, c, d])
        self.assertEqual([b], chooser.choose(dt.Data("a")))
        self.assertEqual([b], chooser.choose(dt.Data("ab")))
        self.assertEqual([a], chooser.choose(dt.Data("abc")))
        self.assertEqual([a], chooser.choose(dt.Data("abcd")))

    def test_range_choice(self):
        a = fld.Field('a', 8, constraints=[Minimum(48), Maximum(57)])
        b = fld.Field('b', 8, constraints=[Equals(dt.Data('['))])
        chooser = chsr.Chooser([a, b])
        self.assertEqual([a], chooser.choose(dt.Data("0")))
        self.assertEqual([b], chooser.choose(dt.Data("[")))

    def test_scaling_of_embedded_choice(self):
        # There was a problem where choosing between items that had multiple 
        # embedded choice items didn't scale.
        lowercase = fld.Field('lowercase', 8, constraints=[Minimum(97), Maximum(122)])
        uppercase = fld.Field('uppercase', 8, constraints=[Minimum(65), Maximum(90)])
        char = chc.Choice('character', [lowercase, uppercase])
        text = seq.Sequence('text', [char, char, char, char, char])

        a = seq.Sequence('a', [fld.Field('a type', 16, constraints=[Equals(dt.Data("BC"))]), text, text, text, text])
        b = seq.Sequence('b', [fld.Field('b type', 16), text, text, text, text])
        chooser = chsr.Chooser([a, b])
        self.assertEqual([a], chooser.choose(dt.Data('BC' + 'a' * 20)))
        self.assertEqual([b], chooser.choose(dt.Data('CD' + 'a' * 20)))

    def test_distinction_after_zero_length_entry(self):
        # There was an error where we would choose the wrong values when the
        # choice came after a zero fields (issue165).
        a = seq.Sequence('a', [
            fld.Field('a1', 8),
            fld.Field('a2', 0),
            fld.Field('a3', 8),
            fld.Field('a4',  8, constraints=[Equals(dt.Data('a'))])])
        b = seq.Sequence('b',  [
            fld.Field('b1', 16),
            fld.Field('b2', 8, constraints=[Equals(dt.Data('b'))])])
        c = fld.Field('c', 8)
        chooser = chsr.Chooser([a, b, c])
        self.assertEqual([a], chooser.choose(dt.Data('xxax')))
        self.assertEqual([b], chooser.choose(dt.Data('xxbx')))
        self.assertEqual([c], chooser.choose(dt.Data('xxcx')))

    def test_sequence_with_equality_constraint(self):
        # There was a bug where a sequence without children, but with
        # constraints, would be reported in the 'successful' list instead of
        # the 'possible' list.
        #
        #   <field name='a' length='8' />
        #   <choice name='b'>
        #      <sequence name='b1' value='${a}' expected='1' />
        #      <field name='b2' length="8" />
        #   </choice>
        b1 = seq.Sequence('b1', [], value=expr.ValueResult('a'),
                constraints=[Equals(1)])
        b2 = fld.Field('b2', length=8)
        chooser = chsr.Chooser([b1, b2])
        self.assertEqual([b1, b2], chooser.choose(dt.Data('x')))

    def test_sequence_with_minimum_constraint(self):
        # Tests for correctly choosing when we have a 'minimum' constraint
        b1 = seq.Sequence('b1', [], value=expr.ValueResult('a'),
                constraints=[Minimum(1)])
        b2 = fld.Field('b2', length=8)
        chooser = chsr.Chooser([b1, b2])
        self.assertEqual([b1, b2], chooser.choose(dt.Data('x')))

    def test_not_enough_data_for_any_option(self):
        a = seq.Sequence('a', [
            fld.Field('a1', length=8),
            fld.Field('a2', length=8, constraints=[Equals(dt.Data('\x00'))])])
        b = seq.Sequence('b', [
            fld.Field('b1', length=8),
            fld.Field('b2', length=8, constraints=[Equals(dt.Data('\x01'))])])
        c = seq.Sequence('c', [])
        chooser = chsr.Chooser([a, b, c])
        self.assertEqual([c], chooser.choose(dt.Data('', 0, 0)))
