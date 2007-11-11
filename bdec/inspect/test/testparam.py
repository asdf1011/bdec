import operator
import unittest

import bdec.choice as chc
import bdec.data as dt
import bdec.field as fld
import bdec.inspect.param as prm
import bdec.sequence as seq
import bdec.sequenceof as sof
import bdec.spec.expression as expr

class TestVariableReference(unittest.TestCase):
    def test_direct_children(self):
        a = fld.Field('a', 8)
        value = expr.ValueResult()
        value.add_entry(a)
        b = fld.Field('b', value)
        spec = seq.Sequence('blah', [a,b])

        vars = prm.VariableReference([spec])
        self.assertEqual(['a'], vars.get_locals(spec))
        self.assertTrue(vars.is_value_referenced(a))
        self.assertFalse(vars.is_value_referenced(b))
        self.assertEqual([], vars.get_locals(a))

    def test_sub_children(self):
        a2 = fld.Field('a2', 8)
        a1 = seq.Sequence('a1', [a2])
        a = seq.Sequence('a', [a1])
        value = expr.ValueResult()
        value.add_entry(a2)
        b1 = fld.Field('b1', value)
        b = seq.Sequence('b', [b1])
        spec = seq.Sequence('blah', [a,b])

        vars = prm.VariableReference([spec])
        self.assertEqual(['a2'], vars.get_locals(spec))
        # Note that despite containing a referenced entry, it isn't a local (as
        # it is passed up to the parent entry).
        self.assertEqual([], vars.get_locals(a))

        # Now check what parameters are passed in and out
        self.assertEqual(set(), set(vars.get_params(spec)))
        self.assertEqual(set([prm.Param('a2', prm.Param.OUT)]), vars.get_params(a2))
        self.assertEqual(set([prm.Param('a2', prm.Param.OUT)]), vars.get_params(a1))
        self.assertEqual(set([prm.Param('a2', prm.Param.OUT)]), vars.get_params(a))
        self.assertEqual(set([prm.Param('a2', prm.Param.IN)]), vars.get_params(b))

    def test_length_reference(self):
        a1 = fld.Field('a1', 8)
        a = seq.Sequence('a', [a1])
        b1 = fld.Field('b1', expr.LengthResult([a]))
        b = seq.Sequence('b', [b1])
        spec = seq.Sequence('blah', [a,b])

        vars = prm.VariableReference([spec])
        self.assertEqual(['a length'], vars.get_locals(spec))
        self.assertFalse(vars.is_length_referenced(a1))
        self.assertTrue(vars.is_length_referenced(a))
        self.assertEqual(set([prm.Param('a length', prm.Param.OUT)]), vars.get_params(a))
        self.assertEqual(set([prm.Param('a length', prm.Param.IN)]), vars.get_params(b))

    def test_sequence_value(self):
        # Define an integer with a custom byte ordering
        lower = fld.Field('lower byte', 8)
        lower_value = expr.ValueResult()
        lower_value.add_entry(lower)
        ignored = fld.Field('ignored', 8)
        upper = fld.Field('upper byte', 8)
        upper_value = expr.ValueResult()
        upper_value.add_entry(upper)
        value = expr.Delayed(operator.__add__, expr.Delayed(operator.__mul__, upper_value, 256), lower_value)
        length = seq.Sequence('length', [lower, ignored, upper], value)
        header = seq.Sequence('header', [length])

        int_value = expr.ValueResult()
        int_value.add_entry(length)
        data = fld.Field('data', int_value)
        spec = seq.Sequence('blah', [length, data])

        vars = prm.VariableReference([spec])
        self.assertTrue(vars.is_value_referenced(lower))
        self.assertFalse(vars.is_value_referenced(ignored))
        self.assertTrue(vars.is_value_referenced(upper))
        self.assertEqual(['lower byte', 'upper byte'], vars.get_locals(length))
        self.assertEqual(set([prm.Param('lower byte', prm.Param.OUT)]), vars.get_params(lower))
        self.assertEqual(set([prm.Param('upper byte', prm.Param.OUT)]), vars.get_params(upper))
        self.assertEqual(set([prm.Param('length', prm.Param.OUT)]), vars.get_params(length))

        self.assertEqual(['length'], vars.get_locals(spec))
        self.assertEqual(set([prm.Param('length', prm.Param.IN)]), vars.get_params(data))


class TestSequenceOfParamLookup(unittest.TestCase):
    def test_end_entry_lookup(self):
        null = fld.Field("null", 8, expected=dt.Data('\x00'))
        char = fld.Field("char", 8)
        entry = chc.Choice('entry', [null, char])
        string = sof.SequenceOf("null terminated string", entry, None, end_entries=[(null, 1)])

        lookup = prm.SequenceOfParamLookup([string])
        self.assertEqual(set([prm.Param('should end', prm.Param.OUT)]), lookup.get_params(null))
        self.assertEqual(set([prm.Param('should end', prm.Param.OUT)]), lookup.get_params(entry))
        self.assertEqual(['should end'], lookup.get_locals(string))
        self.assertTrue(lookup.is_end_sequenceof(null))
