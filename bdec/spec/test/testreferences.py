import unittest

from bdec.entry import Entry
from bdec.spec.references import References

class TestReferences(unittest.TestCase):
    def test_common_references(self):
        # Test that we correctly resolve the case where common entries resolve
        # one another.
        references = References()
        a_ref = references.get_common('b', 'a')
        a = Entry('a', None, [])
        items = references.resolve([a_ref, a])
        self.assertEqual(2, len(items))
        # What should this be??
        self.assertEqual(a, items[0])
        self.assertEqual(a, items[1])
