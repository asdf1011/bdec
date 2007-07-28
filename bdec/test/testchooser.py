
import unittest

import bdec.choice as chc
import bdec.chooser
import bdec.data as dt
import bdec.field as fld
import bdec.sequence as seq

class TestChooser(unittest.TestCase):
    def test_select_single_entry(self):
        chooser = bdec.chooser.Chooser([fld.Field("blah", 8)])
        result = chooser.choose(dt.Data("a"))
        self.assertEqual(1, len(result))

    def test_expected_data(self):
        a = fld.Field("blah", 8, expected=dt.Data('y'))
        chooser = bdec.chooser.Chooser([a])
        self.assertEqual([], chooser.choose(dt.Data("x")))
        self.assertEqual([a], chooser.choose(dt.Data("y")))

    def test_matching_sequence(self):
        a = seq.Sequence("a", [fld.Field("unknown", 8), fld.Field("blah", 8, expected=dt.Data('y'))])
        b = seq.Sequence("b", [fld.Field("blah", 8, expected=dt.Data('z')), fld.Field("unknown", 8)])
        chooser = bdec.chooser.Chooser([a, b])
        self.assertEqual([b], chooser.choose(dt.Data("za")))
        self.assertEqual([a, b], chooser.choose(dt.Data("zy")))
        self.assertEqual([a], chooser.choose(dt.Data("ky")))
        self.assertEqual([], chooser.choose(dt.Data("ab")))

    def test_short_matches_work(self):
        # There was a bug with where an option wouldn't be matched if a longer
        # option matched past the end of the shorter option.
        a = fld.Field("a", 16, expected=dt.Data("yz"))
        b = fld.Field("b", 8)
        chooser = bdec.chooser.Chooser([a, b])
        self.assertEqual([b], chooser.choose(dt.Data("xa")))
        self.assertEqual([a, b], chooser.choose(dt.Data("yz")))
        self.assertEqual([b], chooser.choose(dt.Data("y")))

    def test_ordering_is_maintained(self):
        a = fld.Field("a", 8)
        b = fld.Field("b", 8, expected=dt.Data("y"))
        chooser = bdec.chooser.Chooser([a, b])
        self.assertEqual([a], chooser.choose(dt.Data("x")))
        self.assertEqual([a, b], chooser.choose(dt.Data("y")))

    def test_choose_within_choice(self):
        a = chc.Choice('a', [fld.Field('a1', 8, expected=dt.Data('a')), fld.Field('a2', 8, expected=dt.Data('A'))])
        b = chc.Choice('b', [fld.Field('b1', 8, expected=dt.Data('b')), fld.Field('b2', 8, expected=dt.Data('B'))])
        chooser = bdec.chooser.Chooser([a, b])
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
        a = seq.Sequence("a", [initial, common_choice, fld.Field('a', 8, expected=dt.Data('a'))])
        b = seq.Sequence("b", [initial, common_choice, fld.Field('b', 8, expected=dt.Data('b'))])

        chooser = bdec.chooser.Chooser([a, b])
        self.assertEqual([a], chooser.choose(dt.Data("xya")))
        self.assertEqual([b], chooser.choose(dt.Data("xyb")))
        self.assertEqual([], chooser.choose(dt.Data("xyc")))

    def test_choice_in_choice(self):
        alpha = chc.Choice('alpha', [fld.Field('a', 8, expected=dt.Data('a')), fld.Field('b', 8, expected=dt.Data('b'))])
        num = chc.Choice('num', [fld.Field('1', 8, expected=dt.Data('1')), fld.Field('2', 8, expected=dt.Data('2'))])
        alphanum = chc.Choice('alphanum', [alpha, num])
        other = fld.Field('other', 8)
        chooser = bdec.chooser.Chooser([alphanum, other])
        self.assertEqual([alphanum, other], chooser.choose(dt.Data("1")))
        self.assertEqual([alphanum, other], chooser.choose(dt.Data("a")))
        self.assertEqual([other], chooser.choose(dt.Data("%")))

# Tests for selecting based on amount of data available (not implemented)
#    def test_no_options_with_empty_data(self):
#        chooser = bdec.chooser.Chooser([fld.Field("blah", 8)])
#        result = chooser.choose(dt.Data(""))
#        self.assertEqual(0, len(result))
#
#    def test_only_valid_sizes_selected(self):
#        a = fld.Field("blah", 24)
#        b = fld.Field("blah", 8)
#        c = fld.Field("blah", 32)
#        d = fld.Field("blah", 16)
#        chooser = bdec.chooser.Chooser([a, b, c, d])
#        result = chooser.choose(dt.Data("ab"))
#        self.assertEqual([b, d], result)
