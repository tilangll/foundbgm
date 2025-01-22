import numpy as np
from PIL import Image
import librosa
import requests
from transformers import pipeline
from typing import Dict, Any, List

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
    
    def fetch_music(self, mood: str = 'happy', limit: int = 10) -> List[Dict]:
        endpoint = f"{self.base_url}/tracks/"
        
        params = {
            'client_id': self.client_id,
            'format': 'json',
            'limit': limit,
            'tags': mood,
            'include': 'musicinfo'
        }
        
        try:
            response = requests.get(endpoint, params=params)
            if response.status_code == 200:
                tracks = response.json()['results']
                
                for track in tracks:
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
                
                return tracks
            else:
                print(f"API请求失败: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"获取音乐时出错: {str(e)}")
            return []

class SimpleBGMMatcher:
    def __init__(self):
        self.content_analyzer = SimpleContentAnalyzer()
        self.music_library = SimpleMusicLibrary()
    
    def match_bgm(self, image_path: str, text: str) -> Dict:
        content_features = self.content_analyzer.analyze_content(image_path, text)
        
        mood = 'happy' if content_features['text_sentiment'] > 0.5 else 'sad'
        
        self.music_library.fetch_music(mood=mood, limit=10)
        
        best_match = None
        best_score = float('-inf')
        
        for music_id, music_features in self.music_library.music_database.items():
            score = self._calculate_match_score(content_features, music_features)
            if score > best_score:
                best_score = score
                best_match = music_features
        
        return best_match
    
    def _calculate_match_score(self, content_features: Dict, music_features: Dict) -> float:
        score = 0.0
        
        if content_features['text_sentiment'] > 0.5:
            score += music_features['energy'] * 0.6
        else:
            score += (1 - music_features['energy']) * 0.6
        
        brightness_normalized = content_features['brightness'] / 255.0
        score += (1 - abs(brightness_normalized - music_features['energy'])) * 0.4
        
        return score