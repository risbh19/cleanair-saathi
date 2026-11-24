import unittest
from backend.app.request_limits import RequestLimits


class LimitTests(unittest.TestCase):
    def test_expiry_and_capacity(self):
        limit = RequestLimits(maximum=2, interval=10, capacity=2)
        self.assertTrue(limit.allow("one", 0))
        self.assertTrue(limit.allow("one", 1))
        self.assertFalse(limit.allow("one", 2))
        self.assertTrue(limit.allow("two", 3))
        self.assertFalse(limit.allow("three", 4))
        self.assertTrue(limit.allow("three", 11))
        self.assertFalse(limit.allow("one", 12))
