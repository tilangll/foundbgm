import numpy as np
from PIL import Image
import librosa
import requests
from transformers import pipeline
from typing import Dict, Any, List
import random  # 添加随机模块
from pyncm import apis
import json
from config import NETEASE_PHONE, NETEASE_PASSWORD

class SimpleContentAnalyzer:
    def __init__(self):
        # 修改为使用更基础的中文模型
        self.sentiment_analyzer = pipeline('sentiment-analysis', 
                                        model='bert-base-chinese',
                                        device=-1)  # 使用 CPU
        self.sentiment_cache = {}  # 添加情感分析缓存
    
    def analyze_content(self, image_path: str, text: str) -> Dict[str, Any]:
        features = {}
        
        # 缩小图片尺寸再分析
        img = Image.open(image_path)
        img.thumbnail((300, 300))  # 缩放到较小尺寸
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
        # 登录网易云音乐
        apis.login.LoginViaCellphone(phone=NETEASE_PHONE, password=NETEASE_PASSWORD)
        
        # 添加心情标签
        self.mood_tags = {
            'happy': {
                'all': ['欢快', '治愈', '元气', '快乐'],
                'instrumental': ['轻音乐', '纯音乐', '钢琴', '治愈系'],
                'vocal': ['流行', '欢快', '正能量', '励志']
            },
            'sad': {
                'all': ['伤感', '孤独', '安静', '忧伤'],
                'instrumental': ['钢琴', '轻音乐', '安静', '纯音乐'],
                'vocal': ['伤感', '孤独', '情歌', '失恋']
            },
            'neutral': {
                'all': ['轻音乐', '纯音乐', '背景音乐', '平静'],
                'instrumental': ['轻音乐', '纯音乐', '钢琴曲', '冥想'],
                'vocal': ['民谣', '轻音乐', '小清新', '温暖']
            }
        }
    def _is_instrumental(self, track) -> bool:
        """判断是否为纯音乐"""
        # 通过歌名关键词判断
        instrumental_keywords = ['纯音乐', '钢琴', '轻音乐', 'instrumental', 'piano', '协奏曲', '交响']
        name = track['name'].lower()
        
        # 1. 检查歌名关键词
        if any(keyword in name for keyword in instrumental_keywords):
            return True
            
        # 2. 检查歌手名称
        artist = track['ar'][0]['name'] if track['ar'] else ''
        if any(keyword in artist.lower() for keyword in ['钢琴家', '乐团', 'orchestra']):
            return True
            
        return False

    def fetch_music(self, mood: str = 'happy', limit: int = 10, music_type: str = "全部音乐") -> List[Dict]:
        all_tracks = []
        
        # 根据音乐类型选择标签
        if music_type == "纯音乐":
            tags = self.mood_tags[mood]['instrumental'][:2]
        elif music_type == "带歌词音乐":
            tags = self.mood_tags[mood]['vocal'][:2]
        else:
            tags = self.mood_tags[mood]['all'][:2]
            
        for tag in tags:
            try:
                search_result = apis.cloudsearch.GetSearchResult(tag, stype=1000, limit=2)
                if 'result' not in search_result or 'playlists' not in search_result['result']:
                    continue
                    
                playlists = search_result['result']['playlists']
                
                for playlist in playlists:
                    try:
                        playlist_detail = apis.playlist.GetPlaylistInfo(playlist['id'])
                        if 'playlist' not in playlist_detail or 'tracks' not in playlist_detail['playlist']:
                            continue
                            
                        tracks = playlist_detail['playlist']['tracks']
                        
                        for track in tracks[:10]:
                            try:
                                # 根据音乐类型过滤
                                is_instrumental = self._is_instrumental(track)
                                if (music_type == "纯音乐" and not is_instrumental) or \
                                   (music_type == "带歌词音乐" and is_instrumental):
                                    continue
                                
                                url_info = apis.track.GetTrackAudio([track['id']])
                                if (not url_info or 'data' not in url_info or 
                                    not url_info['data'] or 
                                    not url_info['data'][0].get('url')):
                                    continue
                                
                                audio_url = url_info['data'][0]['url']
                                # 移除URL可访问性检查，因为网易云的URL通常都是可用的
                                
                                track_info = {
                                    'id': str(track['id']),
                                    'name': track['name'],
                                    'artist': track['ar'][0]['name'] if track['ar'] else '未知艺术家',
                                    'duration': track['dt'] // 1000 if 'dt' in track else 0,
                                    'audio_url': audio_url,
                                    'energy': 0.8 if mood == 'happy' else 0.3 if mood == 'sad' else 0.5,
                                    'tempo': 120 if mood == 'happy' else 80 if mood == 'sad' else 100
                                }
                                all_tracks.append(track_info)
                            except Exception as e:
                                continue
                                
                    except Exception as e:
                        continue
            except Exception as e:
                continue
        
        # 清空之前的数据库
        self.music_database.clear()
        
        # 随机选择tracks
        if all_tracks:
            selected_tracks = random.sample(all_tracks, min(limit, len(all_tracks)))
            for track in selected_tracks:
                self.music_database[track['id']] = track
            
            return selected_tracks
        return []

class SimpleBGMMatcher:
    def __init__(self):
        self.content_analyzer = SimpleContentAnalyzer()
        self.music_library = SimpleMusicLibrary()
        self.previous_matches = set()

    def match_bgm(self, image_path: str, text: str, music_type: str = "全部音乐") -> Dict:
        content_features = self.content_analyzer.analyze_content(image_path, text)
        
        # 根据情感值确定心情
        sentiment = content_features['text_sentiment']
        if sentiment > 0.7:
            mood = 'happy'
        elif sentiment < 0.3:
            mood = 'sad'
        else:
            mood = 'neutral'
        
        # 获取新的音乐列表，传入音乐类型参数
        self.music_library.fetch_music(mood=mood, limit=20, music_type=music_type)
        
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