import unittest

class GlobalExchangeSmokeTest(unittest.TestCase):
    def test_import(self):
        import global_exchange
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
