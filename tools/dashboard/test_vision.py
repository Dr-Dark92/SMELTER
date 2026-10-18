import base64
import unittest
from vision import validate_image

class VisionTests(unittest.TestCase):
    def test_png(self):
        raw=bytes([137,80,78,71,13,10,26,10,0])
        encoded=base64.b64encode(raw).decode()
        self.assertEqual(validate_image({"mime":"image/png","base64":encoded}),encoded)
    def test_reject_mismatch(self):
        with self.assertRaises(ValueError):
            validate_image({"mime":"image/jpeg","base64":base64.b64encode(b"not an image").decode()})
    def test_reject_unsupported(self):
        with self.assertRaises(ValueError):
            validate_image({"mime":"image/svg+xml","base64":"AAAA"})
    def test_reject_bad_base64(self):
        with self.assertRaises(ValueError):
            validate_image({"mime":"image/png","base64":"@@@"})

if __name__=="__main__":
    unittest.main()
