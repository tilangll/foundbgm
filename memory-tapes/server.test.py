import importlib.util
import io
import json
import sys
import threading
import unittest
from email.message import Message
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "memory_tape_server", Path(__file__).with_name("memory_tape_server.py")
)
server_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_module)


class ServerPathTest(unittest.TestCase):
    def test_project_root_is_importable(self):
        self.assertEqual(server_module.PROJECT_ROOT, Path(__file__).resolve().parent.parent)
        self.assertIn(str(server_module.PROJECT_ROOT), sys.path)


class FakeMatcher:
    last_error = None

    def match_bgm(self, image_path, text, music_type):
        assert Path(image_path).read_bytes() == b"test image"
        assert text == ""
        assert music_type == "带歌词音乐"
        return {
            "id": "track-1",
            "name": "Test track",
            "artist": "Test artist",
            "audio_url": "https://example.com/track.mp3",
        }


class MatchServerTest(unittest.TestCase):
    def make_handler(self, content_type):
        handler_type = type(
            "TestHandler",
            (server_module.MemoryTapeHandler,),
            {"matcher": FakeMatcher(), "matcher_lock": threading.Lock()},
        )
        handler = object.__new__(handler_type)
        handler.path = "/api/match"
        handler.headers = Message()
        handler.headers["Content-Type"] = content_type
        handler.headers["Content-Length"] = str(len(b"test image"))
        handler.rfile = io.BytesIO(b"test image")
        handler.wfile = io.BytesIO()
        handler.send_response = lambda status: setattr(handler, "status", status)
        handler.send_header = lambda *_: None
        handler.end_headers = lambda: None
        return handler

    def test_matches_uploaded_image(self):
        handler = self.make_handler("image/png")
        handler.do_POST()
        self.assertEqual(handler.status, 200)
        track = json.loads(handler.wfile.getvalue())
        self.assertEqual(track["audio_url"], "https://example.com/track.mp3")

    def test_rejects_non_image(self):
        handler = self.make_handler("text/plain")
        handler.do_POST()
        self.assertEqual(handler.status, 415)


if __name__ == "__main__":
    unittest.main()
