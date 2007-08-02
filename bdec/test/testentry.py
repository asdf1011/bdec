import unittest

import bdec.entry


class TestRange(unittest.TestCase):
    def test_adding_zero_length_range(self):
        a = bdec.entry.Range(0, 0)
        b = bdec.entry.Range(0, 0)
        c = a + b
        self.assertEqual(0, c.min)
        self.assertEqual(0, c.max)
        
    def test_adding_max(self):
        a = bdec.entry.Range(10, 10)
        b = bdec.entry.Range()
        c = a + b
        self.assertEqual(10, c.min)
        self.assertEqual(c.MAX, c.max)

    def test_adding_ranges(self):
        a = bdec.entry.Range(10, 20)
        b = bdec.entry.Range(0, 5)
        c = a + b
        self.assertEqual(10, c.min)
        self.assertEqual(25, c.max)
