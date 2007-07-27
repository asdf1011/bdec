
import unittest

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
