import unittest

import bdec.field as fld
import bdec.inspect.param as prm
import bdec.sequence as seq
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
        a1 = fld.Field('a1', 8)
        a = seq.Sequence('a', [a1])
        value = expr.ValueResult()
        value.add_entry(a1)
        b1 = fld.Field('b1', value)
        b = seq.Sequence('b', [b1])
        spec = seq.Sequence('blah', [a,b])

        vars = prm.VariableReference([spec])
        self.assertEqual(['a1'], vars.get_locals(spec))
        # Note that despite containing a referenced entry, it isn't a local (as
        # it is passed up to the parent entry).
        self.assertEqual([], vars.get_locals(a))

        # Now check what parameters are passed in and out
        self.assertEqual(set(), set(vars.get_params(spec)))
        self.assertEqual(set([prm.Param('a1', prm.Param.OUT)]), vars.get_params(a))
        self.assertEqual(set([prm.Param('a1', prm.Param.IN)]), vars.get_params(b))

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
