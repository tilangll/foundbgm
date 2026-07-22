import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple
from urllib.parse import quote

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
    """Small Internet Archive adapter for openly published audio items."""

    SEARCH_API = "https://archive.org/advancedsearch.php"
    SCRAPE_APIS = (
        "https://archive.org/services/search/v1/scrape",
        "https://api.archive.org/search/v1/scrape",
    )
    METADATA_API = "https://archive.org/metadata"
    DOWNLOAD_BASE = "https://archive.org/download"
    STREAM_BASE = "https://archive.org/serve"

    # Keep the request fan-out bounded so a single match stays responsive.
    SEARCH_ROWS = 18
    METADATA_ITEMS = 10
    MAX_TRACKS = 24
    CACHE_TTL_SECONDS = 600
    REQUEST_TIMEOUT = 10
    AUDIO_VALIDATION_LIMIT = 8
    STREAM_CHECK_TIMEOUT = 6
    STREAM_CHECK_RANGE = "bytes=0-2047"
    AUDIO_EXTENSIONS = {".mp3", ".ogg", ".oga", ".m4a", ".wav"}
    AUDIO_MIME_TYPES = {
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".oga": "audio/ogg",
        ".m4a": "audio/mp4",
        ".wav": "audio/wav",
    }
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
        retries = Retry(
            total=2,
            connect=2,
            read=2,
            status=2,
            backoff_factor=0.35,
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
        errors = []
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
            docs = ((payload.get("response") or {}).get("docs") or [])
            docs = [doc for doc in docs if doc.get("identifier")]
            if docs:
                return docs
        except requests.RequestException as e:
            errors.append(str(e))
        except ValueError:
            errors.append("advancedsearch 返回了无法解析的数据")

        scrape_params = {
            "q": query,
            "fields": "identifier,title,creator,subject",
            "count": "100",
            "sorts": "downloads desc,identifier asc",
        }
        for api_url in self.SCRAPE_APIS:
            try:
                response = self.session.get(
                    api_url,
                    params=scrape_params,
                    timeout=self.REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                payload = response.json()
            except requests.RequestException as e:
                errors.append(str(e))
                continue
            except ValueError:
                errors.append("scrape 返回了无法解析的数据")
                continue

            items = payload.get("items") or []
            docs = [item for item in items if item.get("identifier")]
            if docs:
                return docs[: self.SEARCH_ROWS]

        if errors:
            self.last_error = f"Internet Archive 搜索失败: {errors[-1]}"
        else:
            self.last_error = "Internet Archive 搜索暂时没有返回音乐条目。"
        return []

    def _load_metadata(self, identifier: str) -> Dict[str, Any] | None:
        url = f"{self.METADATA_API}/{quote(identifier, safe='')}"
        try:
            response = self.session.get(
                url,
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
        if "/__macosx/" in lowered or lowered.startswith("__macosx/"):
            return False
        if any(marker in os.path.basename(lowered) for marker in self.SKIP_FILE_MARKERS):
            return False
        if str(file_info.get("private", "")).lower() == "true":
            return False
        raw_size = file_info.get("size")
        if raw_size not in (None, ""):
            try:
                if int(float(raw_size)) <= 0:
                    return False
            except (TypeError, ValueError):
                pass
        return True

    def _audio_url_variants(self, identifier: str, filename: str) -> List[str]:
        encoded_identifier = quote(identifier, safe="")
        encoded_filename = quote(filename, safe="/")
        return [
            f"{self.DOWNLOAD_BASE}/{encoded_identifier}/{encoded_filename}",
            f"{self.STREAM_BASE}/{encoded_identifier}/{encoded_filename}",
        ]

    def _audio_mime_type(self, filename: str) -> str:
        extension = os.path.splitext(filename.lower())[1]
        return self.AUDIO_MIME_TYPES.get(extension, "audio/mpeg")

    def _audio_mime_type_from_response(self, filename: str, content_type: str) -> str:
        mime_type = content_type.split(";", 1)[0].strip().lower()
        if mime_type.startswith("audio/"):
            return mime_type
        return self._audio_mime_type(filename)

    def _is_stream_response_usable(self, filename: str, response: requests.Response) -> bool:
        if response.status_code not in (200, 206):
            return False
        if str(response.url).startswith("http://"):
            # HTTPS Streamlit pages cannot reliably play audio redirected to HTTP.
            return False

        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if content_type.startswith(("text/", "application/json", "application/xml")):
            return False
        if content_type == "application/octet-stream":
            return os.path.splitext(filename.lower())[1] in self.AUDIO_EXTENSIONS
        if content_type and not content_type.startswith("audio/"):
            return False

        content_length = response.headers.get("Content-Length")
        if content_length in ("0", 0):
            return False
        return True

    def _check_audio_url(self, filename: str, url: str) -> Tuple[str, str] | None:
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
                if not self._is_stream_response_usable(filename, response):
                    return None
                mime_type = self._audio_mime_type_from_response(
                    filename,
                    response.headers.get("Content-Type", ""),
                )
                return str(response.url or url), mime_type
        except requests.RequestException:
            return None

    def _resolve_streamable_audio(
        self,
        identifier: str,
        filename: str,
        existing_urls: List[str] | None = None,
    ) -> Tuple[List[str], str] | None:
        candidates = []
        for url in existing_urls or []:
            if url and url not in candidates:
                candidates.append(url)
        for url in self._audio_url_variants(identifier, filename):
            if url not in candidates:
                candidates.append(url)

        for url in candidates:
            checked = self._check_audio_url(filename, url)
            if not checked:
                continue
            working_url, checked_mime_type = checked
            return [working_url], checked_mime_type

        return None

    def validate_track_audio(self, track: Dict[str, Any]) -> Dict[str, Any] | None:
        track_id = str(track.get("id") or "")
        if ":" not in track_id:
            return None
        identifier, filename = track_id.split(":", 1)
        resolved = self._resolve_streamable_audio(
            identifier,
            filename,
            existing_urls=[str(url) for url in track.get("audio_urls", []) if url],
        )
        if not resolved:
            return None
        working_urls, mime_type = resolved
        verified_track = dict(track)
        verified_track["audio_url"] = working_urls[0]
        verified_track["audio_urls"] = working_urls
        verified_track["audio_mime_type"] = mime_type
        return verified_track

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
        preference = {".mp3": 0, ".m4a": 1, ".ogg": 2, ".oga": 3, ".wav": 4}
        audio_files.sort(key=lambda item: preference.get(os.path.splitext(item["name"].lower())[1], 9))

        tracks = []
        for file_info in audio_files[:4]:
            filename = str(file_info["name"])
            file_title = self._clean_file_title(filename)
            track_name = file_title if len(audio_files) > 1 and file_title else title
            energy, tempo = self._track_profile(f"{context} {filename}", mood)
            track_id = f"{identifier}:{filename}"
            audio_urls = self._audio_url_variants(identifier, filename)
            tracks.append(
                {
                    "id": track_id,
                    "name": track_name,
                    "artist": creator,
                    "duration": self._parse_duration(file_info.get("length")),
                    "audio_url": audio_urls[0],
                    "audio_urls": audio_urls,
                    "audio_mime_type": self._audio_mime_type(filename),
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
