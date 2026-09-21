"""Serve the Memory Tape page and reuse yishun's image-to-music matcher.

Run this file from the yishun folder. By default the page is served from the
neighboring ``memory tapes`` folder at http://127.0.0.1:8765/.
"""

import argparse
import json
import logging
import sys
import tempfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock


MAX_IMAGE_BYTES = 20 * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Running a script makes its own directory sys.path[0], not necessarily the
# repository root where the existing matcher module lives.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class MemoryTapeHandler(SimpleHTTPRequestHandler):
    matcher = None
    matcher_lock = Lock()

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/match":
            self.send_json(404, {"error": "接口不存在"})
            return

        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if not content_type.startswith("image/"):
            self.send_json(415, {"error": "请上传图片文件"})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self.send_json(411, {"error": "缺少图片大小"})
            return
        if not 0 < length <= MAX_IMAGE_BYTES:
            self.send_json(413, {"error": "图片不能超过 20 MB"})
            return

        image_path = None
        try:
            image_bytes = self.rfile.read(length)
            if len(image_bytes) != length:
                self.send_json(400, {"error": "图片上传不完整"})
                return
            with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as image_file:
                image_path = Path(image_file.name)
                image_file.write(image_bytes)

            # A single matcher retains the existing recommendation history and cache.
            with self.matcher_lock:
                if self.matcher is None:
                    from simple_bgm_matcher import SimpleBGMMatcher

                    type(self).matcher = SimpleBGMMatcher()
                track = self.matcher.match_bgm(
                    str(image_path), "", music_type="带歌词音乐"
                )
                match_error = self.matcher.last_error

            if not track or not track.get("audio_url"):
                self.send_json(502, {"error": match_error or "暂时没有找到可播放的音乐"})
                return
            self.send_json(
                200,
                {
                    "id": track.get("id"),
                    "name": track.get("name"),
                    "artist": track.get("artist"),
                    "audio_url": track["audio_url"],
                },
            )
        except Exception:
            logging.exception("Music matching failed")
            self.send_json(500, {"error": "音乐匹配暂不可用，请稍后重试"})
        finally:
            if image_path is not None:
                image_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Serve Memory Tape with yishun music matching")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--site-root",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    args = parser.parse_args()
    site_root = args.site_root.resolve()
    if not (site_root / "index.html").is_file():
        parser.error(f"Memory Tape page not found: {site_root / 'index.html'}")

    handler = partial(MemoryTapeHandler, directory=str(site_root))
    with ThreadingHTTPServer((args.host, args.port), handler) as server:
        print(f"Memory Tape: http://{args.host}:{args.port}/")
        server.serve_forever()


if __name__ == "__main__":
    main()
