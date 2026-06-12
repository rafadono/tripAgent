import time
import unittest

try:
    from tripagent.cache import MemoryTTLCache
except Exception as exc:  # pragma: no cover
    MemoryTTLCache = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@unittest.skipIf(MemoryTTLCache is None, f"Missing dependency: {_IMPORT_ERROR}")
class MemoryTTLCacheTests(unittest.TestCase):
    def test_set_get_hit(self):
        cache = MemoryTTLCache()
        cache.set("k1", {"ok": True}, ttl_sec=5)
        self.assertEqual(cache.get("k1"), {"ok": True})

    def test_expired_value_returns_none(self):
        cache = MemoryTTLCache()
        cache.set("k2", 123, ttl_sec=1)
        time.sleep(1.1)
        self.assertIsNone(cache.get("k2"))


if __name__ == "__main__":
    unittest.main()
