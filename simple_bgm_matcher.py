import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

import numpy as np
import requests
from PIL import Image
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class SimpleContentAnalyzer:
    def __init__(self):
        from transformers import pipeline

        self.sentiment_analyzer = pipeline(
            task="sentiment-analysis",
            model="bert-base-chinese",
        )

    def analyze_content(self, image_path: str, text: str) -> Dict[str, Any]:
        features = {}

        img = Image.open(image_path)
        img.thumbnail((300, 300))
        img_array = np.array(img)

        if img_array.dtype == np.uint8:
            features["brightness"] = float(np.mean(img_array))
            features["color_variance"] = float(np.std(img_array))
        else:
            features["brightness"] = float(np.mean(img_array * 255))
            features["color_variance"] = float(np.std(img_array * 255))

        try:
            sentiment = self.sentiment_analyzer(text)
            features["text_sentiment"] = float(sentiment[0]["score"])
        except Exception as e:
            print(f"情感分析出错: {str(e)}")
            features["text_sentiment"] = 0.5

        return features


class SimpleMusicLibrary:
    """Audius adapter that searches tracks and validates stream playback."""

    AUDIUS_API = "https://api.audius.co/v1"
    APP_NAME = "YiShunSceneBGM"

    # Keep requests quick so the UI does not feel stuck when a provider is slow.
    SEARCH_ROWS = 24
    MAX_TRACKS = 24
    CACHE_TTL_SECONDS = 300
    REQUEST_TIMEOUT = 8
    AUDIO_VALIDATION_LIMIT = 10
    STREAM_CHECK_TIMEOUT = 8
    STREAM_CHECK_RANGE = "bytes=0-2047"

    def __init__(self):
        self.music_database: Dict[str, Dict[str, Any]] = {}
        self.last_error = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "YiShun-SceneBGM/0.1"})
        retries = Retry(
            total=1,
            connect=1,
            read=1,
            status=1,
            backoff_factor=0.2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=8, pool_maxsize=8)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.query_cache: Dict[str, tuple[float, List[Dict[str, Any]]]] = {}
        self.mood_tags = {
            "happy": {
                "all": ["indie pop", "summer dance", "upbeat electronic", "feel good"],
                "instrumental": ["instrumental upbeat", "cinematic chill", "lofi upbeat"],
                "vocal": ["indie pop", "dance pop", "summer pop", "upbeat vocal"],
            },
            "sad": {
                "all": ["indie ballad", "melancholy", "piano chill", "slow acoustic"],
                "instrumental": ["sad instrumental", "piano ambient", "cinematic piano"],
                "vocal": ["indie ballad", "acoustic vocal", "sad pop"],
            },
            "neutral": {
                "all": ["chill", "lofi", "ambient electronic", "indie"],
                "instrumental": ["instrumental chill", "ambient", "background music"],
                "vocal": ["indie vocal", "folk song", "acoustic singer"],
            },
        }

    @staticmethod
    def _as_text(value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value or "")

    def _build_queries(self, mood: str, music_type: str) -> List[str]:
        if music_type == "纯音乐":
            queries = self.mood_tags[mood]["instrumental"]
        elif music_type == "带歌词音乐":
            queries = self.mood_tags[mood]["vocal"]
        else:
            queries = self.mood_tags[mood]["all"]
        return list(queries) + self.mood_tags[mood]["all"][:2]

    def _search_items(self, query: str) -> List[Dict[str, Any]]:
        if query == "__trending__":
            endpoint = f"{self.AUDIUS_API}/tracks/trending"
            params = {"limit": self.SEARCH_ROWS, "app_name": self.APP_NAME}
        else:
            endpoint = f"{self.AUDIUS_API}/tracks/search"
            params = {
                "query": query,
                "limit": self.SEARCH_ROWS,
                "app_name": self.APP_NAME,
            }

        try:
            response = self.session.get(
                endpoint,
                params=params,
                timeout=(3.05, self.REQUEST_TIMEOUT),
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as e:
            self.last_error = f"Audius 搜索失败: {str(e)}"
            return []
        except ValueError:
            self.last_error = "Audius 返回了无法解析的数据。"
            return []

        items = payload.get("data") or []
        return [item for item in items if isinstance(item, dict) and item.get("id")]

    @staticmethod
    def _parse_duration(value: Any) -> int:
        if value is None:
            return 0
        try:
            if isinstance(value, str) and ":" in value:
                parts = [int(float(part)) for part in value.split(":")]
                seconds = 0
                for part in parts:
                    seconds = seconds * 60 + part
                return seconds
            return max(0, int(float(value)))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _audio_mime_type_from_response(content_type: str) -> str:
        mime_type = content_type.split(";", 1)[0].strip().lower()
        if mime_type.startswith("audio/"):
            return mime_type
        return "audio/mpeg"

    @staticmethod
    def _is_stream_response_usable(response: requests.Response) -> bool:
        if response.status_code not in (200, 206):
            return False
        if str(response.url).startswith("http://"):
            # HTTPS Streamlit pages cannot reliably play audio redirected to HTTP.
            return False

        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if content_type.startswith(("text/", "application/json", "application/xml")):
            return False
        if content_type and content_type not in ("application/octet-stream",) and not content_type.startswith("audio/"):
            return False

        content_length = response.headers.get("Content-Length")
        if content_length in ("0", 0):
            return False
        return True

    def _check_audio_url(self, url: str) -> Tuple[str, str] | None:
        try:
            with self.session.get(
                url,
                headers={
                    "Accept": "audio/*,*/*",
                    "Range": self.STREAM_CHECK_RANGE,
                },
                stream=True,
                timeout=(3.05, self.STREAM_CHECK_TIMEOUT),
                allow_redirects=True,
            ) as response:
                if not self._is_stream_response_usable(response):
                    return None
                mime_type = self._audio_mime_type_from_response(response.headers.get("Content-Type", ""))
                # Keep the Audius API endpoint, not the short-lived signed redirect URL.
                return url, mime_type
        except requests.RequestException:
            return None

    def validate_track_audio(self, track: Dict[str, Any]) -> Dict[str, Any] | None:
        existing_urls = [str(url) for url in track.get("audio_urls", []) if url]
        for url in existing_urls:
            checked = self._check_audio_url(url)
            if not checked:
                continue
            working_url, mime_type = checked
            verified_track = dict(track)
            verified_track["audio_url"] = working_url
            verified_track["audio_urls"] = [working_url]
            verified_track["audio_mime_type"] = mime_type
            return verified_track
        return None

    @staticmethod
    def _track_profile(text: str, mood: str) -> tuple[float, int]:
        lowered = text.lower()
        if any(word in lowered for word in ["upbeat", "happy", "dance", "summer", "pop", "electronic", "dubstep"]):
            return 0.82, 122
        if any(word in lowered for word in ["sad", "melancholic", "melancholy", "piano", "ballad"]):
            return 0.28, 78
        if any(word in lowered for word in ["ambient", "calm", "chill", "background"]):
            return 0.42, 92
        return {
            "happy": (0.72, 116),
            "sad": (0.32, 82),
            "neutral": (0.5, 98),
        }[mood]

    @staticmethod
    def _matches_music_type(text: str, music_type: str) -> bool:
        lowered = text.lower()
        vocal_hint = any(
            word in lowered
            for word in [
                "vocal",
                "singer",
                "lyrics",
                "song",
                "voice",
                "feat",
                "ft.",
                "featuring",
            ]
        )
        instrumental_hint = any(
            word in lowered
            for word in ["instrumental", "ambient", "piano", "soundtrack", "background", "lofi", "beat"]
        )
        if music_type == "纯音乐":
            return instrumental_hint or not vocal_hint
        if music_type == "带歌词音乐":
            # Audius metadata rarely marks lyrics explicitly, so do not over-filter.
            return True
        return True

    def _stream_url(self, track_id: str) -> str:
        return f"{self.AUDIUS_API}/tracks/{track_id}/stream?app_name={self.APP_NAME}"

    @staticmethod
    def _source_url(track: Dict[str, Any]) -> str:
        permalink = str(track.get("permalink") or "")
        if permalink.startswith("http"):
            return permalink
        if permalink.startswith("/"):
            return f"https://audius.co{permalink}"
        return "https://audius.co"

    def _extract_track(
        self,
        track: Dict[str, Any],
        mood: str,
        music_type: str,
    ) -> Dict[str, Any] | None:
        track_id = str(track.get("id") or "")
        if not track_id:
            return None

        user = track.get("user") if isinstance(track.get("user"), dict) else {}
        title = self._as_text(track.get("title")) or "Audius Track"
        artist = self._as_text(user.get("name")) or self._as_text(user.get("handle")) or "Audius Artist"
        genre = self._as_text(track.get("genre"))
        tags = self._as_text(track.get("tags") or track.get("mood"))
        description = self._as_text(track.get("description"))
        context = f"{title} {artist} {genre} {tags} {description}"
        if not self._matches_music_type(context, music_type):
            return None

        energy, tempo = self._track_profile(context, mood)
        stream_url = self._stream_url(track_id)
        return {
            "id": f"audius:{track_id}",
            "provider": "Audius",
            "name": title,
            "artist": artist,
            "duration": self._parse_duration(track.get("duration")),
            "audio_url": stream_url,
            "audio_urls": [stream_url],
            "audio_mime_type": "audio/mpeg",
            "lyricist": "未知",
            "composer": artist,
            "energy": energy,
            "tempo": tempo,
            "license_url": None,
            "source_url": self._source_url(track),
            "album": genre or "Audius",
        }

    def fetch_music(
        self,
        mood: str = "happy",
        limit: int = 20,
        music_type: str = "全部音乐",
    ) -> List[Dict[str, Any]]:
        cache_key = f"audius:{mood}:{music_type}"
        cached = self.query_cache.get(cache_key)
        if cached and time.time() - cached[0] < self.CACHE_TTL_SECONDS:
            candidates = cached[1]
        else:
            candidates = []
            queries = self._build_queries(mood, music_type)
            if music_type != "全部音乐":
                queries.extend(self._build_queries(mood, "全部音乐")[:2])
            queries.append("__trending__")

            for query in queries:
                items = self._search_items(query)
                if not items:
                    continue

                for item in items:
                    track = self._extract_track(item, mood, music_type)
                    if not track:
                        continue
                    candidates.append(track)
                    if len(candidates) >= self.MAX_TRACKS:
                        break

                if candidates:
                    break

            unique = {}
            for track in candidates:
                unique.setdefault(track["id"], track)
            candidates = list(unique.values())[: self.MAX_TRACKS]
            self.query_cache[cache_key] = (time.time(), candidates)

        if not candidates:
            self.last_error = "Audius 没有返回可用音乐，请再试一次。"
            return []

        selected = random.sample(candidates, min(limit, len(candidates)))
        self.music_database = {track["id"]: track for track in selected}
        self.last_error = None
        return selected


class SimpleBGMMatcher:
    def __init__(self):
        self.content_analyzer = SimpleContentAnalyzer()
        self.music_library = SimpleMusicLibrary()
        self.previous_matches = set()
        self.last_error = None

    def match_bgm(
        self,
        image_path: str,
        text: str,
        music_type: str = "全部音乐",
    ) -> Dict | None:
        self.last_error = None
        content_features = self.content_analyzer.analyze_content(image_path, text)

        sentiment = content_features["text_sentiment"]
        if sentiment > 0.7:
            mood = "happy"
        elif sentiment < 0.3:
            mood = "sad"
        else:
            mood = "neutral"

        tracks = self.music_library.fetch_music(
            mood=mood,
            limit=20,
            music_type=music_type,
        )
        if not tracks:
            self.last_error = self.music_library.last_error or "未获取到可用音乐"
            return None

        matches = []
        for music_id, music_features in self.music_library.music_database.items():
            if music_id in self.previous_matches:
                continue
            score = self._calculate_match_score(content_features, music_features)
            matches.append((music_id, score, music_features))

        if not matches:
            self.previous_matches.clear()
            matches = [
                (
                    music_features["id"],
                    self._calculate_match_score(content_features, music_features),
                    music_features,
                )
                for music_features in self.music_library.music_database.values()
            ]

        if not matches:
            self.last_error = "当前没有可用的新歌曲可供推荐"
            return None

        matches.sort(key=lambda item: item[1], reverse=True)
        validation_matches = matches[: self.music_library.AUDIO_VALIDATION_LIMIT]
        verified_by_id: Dict[str, Dict[str, Any]] = {}

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(
                    self.music_library.validate_track_audio,
                    music_features,
                ): music_id
                for music_id, _, music_features in validation_matches
            }
            for future in as_completed(futures):
                music_id = futures[future]
                try:
                    verified_track = future.result()
                except Exception:
                    verified_track = None
                if verified_track:
                    verified_by_id[music_id] = verified_track

        verified_matches = [
            (score, verified_by_id[music_id])
            for music_id, score, _ in validation_matches
            if music_id in verified_by_id
        ]
        if not verified_matches:
            self.last_error = "匹配到了歌曲，但可播放音频源暂时连不上，请再试一次。"
            return None

        top_matches = verified_matches[:3]
        score, best_match = random.choice(top_matches)
        self.previous_matches.add(best_match["id"])
        result = best_match.copy()
        result["match_score"] = float(score)
        result["content_features"] = content_features
        return result

    def _calculate_match_score(
        self,
        content_features: Dict[str, Any],
        music_features: Dict[str, Any],
    ) -> float:
        score = 0.0
        sentiment_diff = abs(
            content_features["text_sentiment"] - music_features["energy"]
        )
        score -= sentiment_diff * 0.4

        brightness_normalized = content_features["brightness"] / 255.0
        score -= abs(brightness_normalized - music_features["energy"]) * 0.3

        score += random.uniform(0, 0.3)
        return score
