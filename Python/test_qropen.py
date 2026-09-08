import http.client
import tempfile
import threading
import unittest
from pathlib import Path

from qropen import MAX_UPLOAD, TUNNEL_URL, make_handler
from http.server import ThreadingHTTPServer


class TransferTest(unittest.TestCase):
    def test_quick_tunnel_url(self):
        log = "Your quick Tunnel has been created! Visit it at https://fast-demo.trycloudflare.com"
        self.assertEqual(TUNNEL_URL.search(log).group(0), "https://fast-demo.trycloudflare.com")

    def test_upload_download_and_safe_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(folder, "secret"))
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
                connection.request("POST", "/secret/upload", b"hello", {"X-Filename": "../note.txt"})
                self.assertEqual(connection.getresponse().status, 201)
                connection.request("POST", "/secret/upload", b"again", {"X-Filename": "note.txt"})
                self.assertEqual(connection.getresponse().status, 201)
                connection.request("POST", "/secret/upload", b"windows", {"X-Filename": "..%5Cwindows.txt"})
                self.assertEqual(connection.getresponse().status, 201)
                connection.request("GET", "/secret/files/note.txt")
                response = connection.getresponse()
                self.assertEqual((response.status, response.getheader("Cache-Control"), response.read()), (200, "no-store, private", b"hello"))
                connection.request("GET", "/secret/")
                page = connection.getresponse().read()
                self.assertIn(b'<html lang="en">', page)
                self.assertIn(b"Send to computer", page)
                connection.request("POST", "/secret/upload", headers={"Content-Length": str(MAX_UPLOAD + 1)})
                self.assertEqual(connection.getresponse().status, 413)
                self.assertEqual((folder / "note (1).txt").read_bytes(), b"again")
                self.assertEqual((folder / "windows.txt").read_bytes(), b"windows")
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == "__main__":
    unittest.main()
