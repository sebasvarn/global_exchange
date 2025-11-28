import unittest

class CommonsSmokeTest(unittest.TestCase):
    def test_import(self):
        import commons
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
