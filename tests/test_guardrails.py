import unittest

try:
    from tripagent.guardrails import SlidingWindowRateLimiter
except Exception as exc:  # pragma: no cover
    SlidingWindowRateLimiter = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@unittest.skipIf(SlidingWindowRateLimiter is None, f"Missing dependency: {_IMPORT_ERROR}")
class RateLimiterTests(unittest.TestCase):
    def test_allow_until_limit(self):
        limiter = SlidingWindowRateLimiter()
        ok1, rem1 = limiter.allow("a", limit=2, window_sec=60)
        ok2, rem2 = limiter.allow("a", limit=2, window_sec=60)
        ok3, rem3 = limiter.allow("a", limit=2, window_sec=60)
        self.assertTrue(ok1)
        self.assertEqual(rem1, 1)
        self.assertTrue(ok2)
        self.assertEqual(rem2, 0)
        self.assertFalse(ok3)
        self.assertEqual(rem3, 0)


if __name__ == "__main__":
    unittest.main()
