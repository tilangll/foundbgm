import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List
from urllib.parse import quote

import numpy as np
import requests
from PIL import Image


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
    """Small Internet Archive adapter for openly published audio items."""

    SEARCH_API = "https://archive.org/advancedsearch.php"
    METADATA_API = "https://archive.org/metadata"
    DOWNLOAD_BASE = "https://archive.org/download"

    # Keep the request fan-out bounded so a single match stays responsive.
    SEARCH_ROWS = 18
    METADATA_ITEMS = 10
    MAX_TRACKS = 24
    CACHE_TTL_SECONDS = 600
    REQUEST_TIMEOUT = 10
    AUDIO_EXTENSIONS = {".mp3", ".ogg", ".oga", ".m4a", ".wav"}
    SKIP_FILE_MARKERS = {
        "cover",
        "thumbnail",
        "spectrogram",
        "waveform",
        "sample",
        "preview",
        "readme",
    }

    def __init__(self):
        self.music_database: Dict[str, Dict[str, Any]] = {}
        self.last_error = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "YiShun-SceneBGM/0.1"})
        self.query_cache: Dict[str, tuple[float, List[Dict[str, Any]]]] = {}
        self.mood_tags = {
            "happy": {
                "all": ["upbeat", "happy", "summer", "pop"],
                "instrumental": ["instrumental", "upbeat", "cinematic", "ambient"],
                "vocal": ["vocal", "pop", "indie", "dance"],
            },
            "sad": {
                "all": ["sad", "melancholic", "piano", "chill"],
                "instrumental": ["instrumental", "piano", "ambient", "sad"],
                "vocal": ["vocal", "acoustic", "indie", "ballad"],
            },
            "neutral": {
                "all": ["chill", "calm", "ambient", "indie"],
                "instrumental": ["instrumental", "ambient", "calm", "background"],
                "vocal": ["vocal", "folk", "acoustic", "indie"],
            },
        }

    @staticmethod
    def _as_text(value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value or "")

    def _build_query(self, mood: str, music_type: str, broad: bool = False) -> str:
        if music_type == "纯音乐":
            tags = self.mood_tags[mood]["instrumental"]
        elif music_type == "带歌词音乐":
            tags = self.mood_tags[mood]["vocal"]
        else:
            tags = self.mood_tags[mood]["all"]

        tag_query = " OR ".join(
            f"title:{tag} OR subject:{tag}" for tag in tags[:4]
        )
        source_filter = "mediatype:audio" if broad else "collection:netlabels AND mediatype:audio"
        return f"{source_filter} AND ({tag_query})"

    def _search_items(self, query: str) -> List[Dict[str, Any]]:
        params = [
            ("q", query),
            ("fl[]", "identifier"),
            ("fl[]", "title"),
            ("fl[]", "creator"),
            ("fl[]", "subject"),
            ("rows", str(self.SEARCH_ROWS)),
            ("page", "1"),
            ("output", "json"),
            ("sort[]", "downloads desc"),
        ]

        try:
            response = self.session.get(
                self.SEARCH_API,
                params=params,
                timeout=self.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as e:
            self.last_error = f"Internet Archive 搜索失败: {str(e)}"
            return []
        except ValueError:
            self.last_error = "Internet Archive 返回了无法解析的数据。"
            return []

        docs = ((payload.get("response") or {}).get("docs") or [])
        return [doc for doc in docs if doc.get("identifier")]

    def _load_metadata(self, identifier: str) -> Dict[str, Any] | None:
        url = f"{self.METADATA_API}/{quote(identifier, safe='')}"
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "YiShun-SceneBGM/0.1"},
                timeout=self.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return None
        return payload if payload.get("files") else None

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
    def _clean_file_title(filename: str) -> str:
        stem = os.path.splitext(os.path.basename(filename))[0]
        stem = re.sub(r"[_-]+", " ", stem)
        stem = re.sub(r"\s+", " ", stem).strip()
        return stem

    def _is_usable_audio_file(self, file_info: Dict[str, Any]) -> bool:
        filename = str(file_info.get("name") or "")
        lowered = filename.lower()
        extension = os.path.splitext(lowered)[1]
        if extension not in self.AUDIO_EXTENSIONS:
            return False
        if any(marker in os.path.basename(lowered) for marker in self.SKIP_FILE_MARKERS):
            return False
        if str(file_info.get("private", "")).lower() == "true":
            return False
        return True

    @staticmethod
    def _track_profile(text: str, mood: str) -> tuple[float, int]:
        lowered = text.lower()
        if any(word in lowered for word in ["upbeat", "happy", "dance", "summer", "pop"]):
            return 0.82, 122
        if any(word in lowered for word in ["sad", "melancholic", "piano", "ballad"]):
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
            for word in ["instrumental", "ambient", "piano", "soundtrack", "background"]
        )
        if music_type == "纯音乐":
            return not vocal_hint
        if music_type == "带歌词音乐":
            return vocal_hint or not instrumental_hint
        return True

    def _extract_tracks(
        self,
        identifier: str,
        payload: Dict[str, Any],
        mood: str,
        music_type: str,
    ) -> List[Dict[str, Any]]:
        metadata = payload.get("metadata") or {}
        title = self._as_text(metadata.get("title")) or identifier
        creator = self._as_text(metadata.get("creator")) or "Internet Archive Artist"
        subjects = self._as_text(metadata.get("subject"))
        description = self._as_text(metadata.get("description"))
        context = f"{title} {creator} {subjects} {description}"
        if not self._matches_music_type(context, music_type):
            return []

        audio_files = [
            file_info
            for file_info in payload.get("files", [])
            if isinstance(file_info, dict) and self._is_usable_audio_file(file_info)
        ]
        preference = {".mp3": 0, ".ogg": 1, ".oga": 2, ".m4a": 3, ".wav": 4}
        audio_files.sort(key=lambda item: preference.get(os.path.splitext(item["name"].lower())[1], 9))

        tracks = []
        for file_info in audio_files[:4]:
            filename = str(file_info["name"])
            file_title = self._clean_file_title(filename)
            track_name = file_title if len(audio_files) > 1 and file_title else title
            energy, tempo = self._track_profile(f"{context} {filename}", mood)
            track_id = f"{identifier}:{filename}"
            audio_url = (
                f"{self.DOWNLOAD_BASE}/{quote(identifier, safe='')}/"
                f"{quote(filename, safe='/')}"
            )
            tracks.append(
                {
                    "id": track_id,
                    "name": track_name,
                    "artist": creator,
                    "duration": self._parse_duration(file_info.get("length")),
                    "audio_url": audio_url,
                    "lyricist": "未知",
                    "composer": creator,
                    "energy": energy,
                    "tempo": tempo,
                    "license_url": metadata.get("licenseurl") or metadata.get("license"),
                    "source_url": f"https://archive.org/details/{quote(identifier, safe='')}",
                    "album": title,
                }
            )
        return tracks

    def fetch_music(
        self,
        mood: str = "happy",
        limit: int = 20,
        music_type: str = "全部音乐",
    ) -> List[Dict[str, Any]]:
        cache_key = f"{mood}:{music_type}"
        cached = self.query_cache.get(cache_key)
        if cached and time.time() - cached[0] < self.CACHE_TTL_SECONDS:
            candidates = cached[1]
        else:
            candidates = []
            queries = [
                self._build_query(mood, music_type),
                self._build_query(mood, music_type, broad=True),
            ]
            if music_type != "全部音乐":
                queries.append(self._build_query(mood, "全部音乐", broad=True))

            for query in queries:
                items = self._search_items(query)
                if not items:
                    continue

                metadata_items = items[: self.METADATA_ITEMS]
                payloads: Dict[str, Dict[str, Any]] = {}
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = {
                        executor.submit(self._load_metadata, item["identifier"]): item["identifier"]
                        for item in metadata_items
                    }
                    for future in as_completed(futures):
                        identifier = futures[future]
                        payload = future.result()
                        if payload:
                            payloads[identifier] = payload

                for item in metadata_items:
                    identifier = item["identifier"]
                    payload = payloads.get(identifier)
                    if not payload:
                        continue
                    candidates.extend(
                        self._extract_tracks(identifier, payload, mood, music_type)
                    )
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
            self.last_error = "Internet Archive 返回了条目，但没有找到可播放的音频文件。"
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
            matches.append((score, music_features))

        if not matches:
            self.previous_matches.clear()
            matches = [
                (
                    self._calculate_match_score(content_features, music_features),
                    music_features,
                )
                for music_features in self.music_library.music_database.values()
            ]

        if not matches:
            self.last_error = "当前没有可用的新歌曲可供推荐"
            return None

        matches.sort(key=lambda item: item[0], reverse=True)
        top_matches = matches[:3]
        _, best_match = random.choice(top_matches)
        self.previous_matches.add(best_match["id"])
        return best_match

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
