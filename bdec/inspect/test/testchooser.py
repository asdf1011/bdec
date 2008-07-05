
import unittest

import bdec.choice as chc
import bdec.data as dt
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
        a = seq.Sequence("a", [fld.Field("unknown a", 8), fld.Field("blah", 8, expected=dt.Data('y'))])
        b = seq.Sequence("b", [fld.Field("blah", 8, expected=dt.Data('z')), fld.Field("unknown b", 8)])
        chooser = chsr.Chooser([a, b])
        self.assertEqual([b], chooser.choose(dt.Data("za")))
        # Note that 'b' shouldn't be possible, as 'a' must be successful
        self.assertEqual([a], chooser.choose(dt.Data("zy")))
        self.assertEqual([a], chooser.choose(dt.Data("ky")))

    def test_short_matches_work(self):
        # There was a bug with where an option wouldn't be matched if a longer
        # option matched past the end of the shorter option.
        a = fld.Field("a", 16, expected=dt.Data("yz"))
        b = fld.Field("b", 8)
        chooser = chsr.Chooser([a, b])
        self.assertEqual([b], chooser.choose(dt.Data("xa")))
        self.assertEqual([a, b], chooser.choose(dt.Data("yz")))
        # FIXME: We currently don't distinguish based on the amount of data
        # available.
        #self.assertEqual([b], chooser.choose(dt.Data("y")))

    def test_choose_within_choice(self):
        a = chc.Choice('a', [fld.Field('a1', 8, expected=dt.Data('a')), fld.Field('a2', 8, expected=dt.Data('A'))])
        b = chc.Choice('b', [fld.Field('b1', 8, expected=dt.Data('b')), fld.Field('b2', 8, expected=dt.Data('B'))])
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
        a = seq.Sequence("a", [initial, common_choice, fld.Field('a', 8, expected=dt.Data('a'))])
        b = seq.Sequence("b", [initial, common_choice, fld.Field('b', 8, expected=dt.Data('b'))])

        chooser = chsr.Chooser([a, b])
        self.assertEqual([a], chooser.choose(dt.Data("xya")))
        self.assertEqual([b], chooser.choose(dt.Data("xyb")))
        self.assertEqual([], chooser.choose(dt.Data("xyc")))

    def test_choice_in_choice(self):
        alpha = chc.Choice('alpha', [fld.Field('a', 8, expected=dt.Data('a')), fld.Field('b', 8, expected=dt.Data('b'))])
        num = chc.Choice('num', [fld.Field('1', 8, expected=dt.Data('1')), fld.Field('2', 8, expected=dt.Data('2'))])
        alphanum = chc.Choice('alphanum', [alpha, num])
        other = fld.Field('other', 8)
        chooser = chsr.Chooser([alphanum, other])
        self.assertEqual([alphanum], chooser.choose(dt.Data("1")))
        self.assertEqual([alphanum], chooser.choose(dt.Data("a")))
        self.assertEqual([other], chooser.choose(dt.Data("%")))

    #def test_min_max_differentiation(self):
    #    # Some entries have a valid range of values, and so it is convenient
    #    # to offer them as a choice of fields with a min and max value (eg:
    #    # for pdf 'names' only certain characters are valid). It would be
    #    # good to differentiate on these.
    #    a = fld.Field("a", 8, min=0x10, max=0x20)
    #    b = fld.Field("b", 8, min=0x25, max=0x35)
    #    chooser = chsr.Chooser([a, b])
    #    self.assertEqual([], chooser.choose(dt.Data("\x0f")))
    #    self.assertEqual([a], chooser.choose(dt.Data("\x10")))
    #    self.assertEqual([a], chooser.choose(dt.Data("\x20")))
    #    self.assertEqual([], chooser.choose(dt.Data("\x21")))
    #    self.assertEqual([b], chooser.choose(dt.Data("\x25")))

    def test_ignores_later_options_when_option_fully_decodes(self):
        # If we get an option that we believe fully decodes, don't list any items
        # lower in the priority chain as potentials.
        a = fld.Field("a", 8, expected=dt.Data('\x00'))
        b = fld.Field("b", 8)
        chooser = chsr.Chooser([a, b])
        self.assertEqual([a], chooser.choose(dt.Data("\x00")))
        self.assertEqual([b], chooser.choose(dt.Data("\x01")))

#    def test_string_representation(self):
#        a = seq.Sequence("a", [fld.Field("common", 8, expected=dt.Data('c')), fld.Field("a id", 8, expected=dt.Data('y'))])
#        b = seq.Sequence("b", [fld.Field("common", 8, expected=dt.Data('c')), fld.Field("b id", 8, expected=dt.Data('z'))])
#        chooser = chsr.Chooser([a, b])
#        self.assertEqual("bits [8, 16) key={121: [<class 'bdec.sequence.Sequence'> 'a'], 122: [<class 'bdec.sequence.Sequence'> 'b']} fallback=[]", str(chooser))

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
        a = fld.Field('a', 8, min=48, max=57)
        b = fld.Field('b', 8, expected=dt.Data('['))
        chooser = chsr.Chooser([a, b])
        self.assertEqual([a], chooser.choose(dt.Data("0")))
        self.assertEqual([a, b], chooser.choose(dt.Data("[")))
