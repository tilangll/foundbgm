import time
from simple_bgm_matcher import SimpleBGMMatcher

def test_music_matching():
    matcher = SimpleBGMMatcher()
    
    # 测试图片路径
    image_path = "./test_image.jpg"  # 请确保这个路径指向一个真实的测试图片
    test_text = "今天天气真好，心情愉快"
    
    print("开始测试音乐匹配...")
    
    # 测试性能
    start_time = time.time()
    try:
        # 测试不同音乐类型
        for music_type in ["全部音乐", "纯音乐", "带歌词音乐"]:
            print(f"\n测试{music_type}匹配:")
            match_start = time.time()
            result = matcher.match_bgm(image_path, test_text, music_type)
            match_end = time.time()
            
            print(f"匹配结果: {result.get('name')} - {result.get('artist')}")
            print(f"匹配用时: {match_end - match_start:.2f} 秒")
        
        end_time = time.time()
        print(f"\n总处理时间: {end_time - start_time:.2f} 秒")
        
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")

if __name__ == "__main__":
    test_music_matching()