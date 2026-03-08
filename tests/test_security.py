import hashlib
import unittest

from app.security import (
    create_access_token,
    decode_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)


class SecurityTests(unittest.TestCase):
    def test_bcrypt_password_round_trip(self):
        hashed = hash_password("correct horse battery staple")
        self.assertTrue(hashed.startswith("$2"))
        self.assertTrue(verify_password("correct horse battery staple", hashed))
        self.assertFalse(password_needs_rehash(hashed))

    def test_legacy_sha256_hashes_still_verify_and_require_upgrade(self):
        legacy_hash = hashlib.sha256("password123".encode()).hexdigest()
        self.assertTrue(verify_password("password123", legacy_hash))
        self.assertTrue(password_needs_rehash(legacy_hash))

    def test_access_token_round_trip(self):
        token = create_access_token("user-1", "alex@example.com")
        decoded = decode_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded.user_id, "user-1")
        self.assertEqual(decoded.email, "alex@example.com")


if __name__ == "__main__":
    unittest.main()
