import numpy as np
from PIL import Image
import librosa
import requests
from transformers import pipeline
from typing import Dict, Any, List
import random  # 添加随机模块

class SimpleContentAnalyzer:
    def __init__(self):
        # 修改为使用更基础的中文模型
        self.sentiment_analyzer = pipeline('sentiment-analysis', 
                                        model='bert-base-chinese',
                                        device=-1)  # 使用 CPU
    
    def analyze_content(self, image_path: str, text: str) -> Dict[str, Any]:
        features = {}
        
        # 分析图片
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # 确保图片数据类型正确
        if img_array.dtype == np.uint8:
            features['brightness'] = float(np.mean(img_array))
            features['color_variance'] = float(np.std(img_array))
        else:
            features['brightness'] = float(np.mean(img_array * 255))
            features['color_variance'] = float(np.std(img_array * 255))
        
        # 分析文字情感
        try:
            sentiment = self.sentiment_analyzer(text)
            features['text_sentiment'] = sentiment[0]['score']
        except Exception as e:
            print(f"情感分析出错: {str(e)}")
            features['text_sentiment'] = 0.5  # 默认中性情感
        
        return features

class SimpleMusicLibrary:
    def __init__(self):
        self.music_database = {}
        self.client_id = "47b332a2"
        self.base_url = "https://api.jamendo.com/v3.0"
        self.mood_tags = {
            'happy': ['happy', 'upbeat', 'energetic', 'positive'],
            'sad': ['sad', 'melancholic', 'calm', 'peaceful'],
            'neutral': ['ambient', 'instrumental', 'relaxing']
        }

    def fetch_music(self, mood: str = 'happy', limit: int = 10) -> List[Dict]:
        endpoint = f"{self.base_url}/tracks/"
        tags = self.mood_tags.get(mood, self.mood_tags['neutral'])
        all_tracks = []
        
        for tag in tags:
            params = {
                'client_id': self.client_id,
                'format': 'json',
                'limit': limit,
                'tags': tag,
                'include': 'musicinfo',
                'orderby': 'random'  # 添加随机排序
            }
            
            try:
                response = requests.get(endpoint, params=params)
                if response.status_code == 200:
                    tracks = response.json()['results']
                    all_tracks.extend(tracks)
            except Exception as e:
                print(f"获取音乐时出错: {str(e)}")
                continue
        
        # 清空之前的数据库
        self.music_database.clear()
        
        # 随机选择tracks
        if all_tracks:
            selected_tracks = random.sample(all_tracks, min(limit, len(all_tracks)))
            for track in selected_tracks:
                track_info = {
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artist_name'],
                    'duration': track['duration'],
                    'audio_url': track['audio'],
                    'license': track['license_ccurl'],
                    'mood_tags': track.get('tags', []),
                    'energy': float(track.get('musicinfo', {}).get('energy', 0.5)),
                    'tempo': float(track.get('musicinfo', {}).get('bpm', 120))
                }
                self.music_database[track['id']] = track_info
            
            return selected_tracks
        return []

class SimpleBGMMatcher:
    def __init__(self):
        self.content_analyzer = SimpleContentAnalyzer()
        self.music_library = SimpleMusicLibrary()
        self.previous_matches = set()  # 记录之前的匹配
    
    def match_bgm(self, image_path: str, text: str) -> Dict:
        content_features = self.content_analyzer.analyze_content(image_path, text)
        
        # 根据情感值确定心情
        sentiment = content_features['text_sentiment']
        if sentiment > 0.7:
            mood = 'happy'
        elif sentiment < 0.3:
            mood = 'sad'
        else:
            mood = 'neutral'
        
        # 获取新的音乐列表
        self.music_library.fetch_music(mood=mood, limit=20)
        
        # 计算所有可能的匹配
        matches = []
        for music_id, music_features in self.music_library.music_database.items():
            if music_id not in self.previous_matches:  # 避免重复推荐
                score = self._calculate_match_score(content_features, music_features)
                matches.append((score, music_features))
        
        # 如果没有新的匹配，重置历史记录
        if not matches:
            self.previous_matches.clear()
            return self.match_bgm(image_path, text)
        
        # 从前三首最佳匹配中随机选择一首
        matches.sort(key=lambda x: x[0], reverse=True)
        top_matches = matches[:3]
        _, best_match = random.choice(top_matches)
        
        # 记录这次的匹配
        self.previous_matches.add(best_match['id'])
        
        return best_match

    def _calculate_match_score(self, content_features: Dict, music_features: Dict) -> float:
        score = 0.0
        
        # 考虑情感值的细微差别
        sentiment_diff = abs(content_features['text_sentiment'] - music_features['energy'])
        score -= sentiment_diff * 0.4
        
        # 考虑亮度和音乐能量的匹配
        brightness_normalized = content_features['brightness'] / 255.0
        score -= abs(brightness_normalized - music_features['energy']) * 0.3
        
        # 添加一些随机性
        score += random.uniform(0, 0.3)
        
        return score