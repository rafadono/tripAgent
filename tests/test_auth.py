import unittest
from types import SimpleNamespace

try:
    from tripagent.auth import _users_map
except Exception as exc:  # pragma: no cover
    _users_map = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@unittest.skipIf(_users_map is None, f"Missing dependency: {_IMPORT_ERROR}")
class AuthTests(unittest.TestCase):
    def test_users_map(self):
        settings = SimpleNamespace(auth_users=("a:1", "b:2", "bad"))
        users = _users_map(settings)
        self.assertEqual(users["a"], "1")
        self.assertEqual(users["b"], "2")
        self.assertNotIn("bad", users)


if __name__ == "__main__":
    unittest.main()
