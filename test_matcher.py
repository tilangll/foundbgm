from simple_bgm_matcher import SimpleBGMMatcher

def test_bgm_matching():
    matcher = SimpleBGMMatcher()
    
    # 测试一个简单的场景
    try:
        result = matcher.match_bgm(
            image_path="test_image.jpg",  # 请确保这个图片文件存在
            text="今天是个阳光明媚的好日子",
            music_type="全部音乐"
        )
        
        print("匹配成功！")
        print(f"推荐音乐: {result['name']} - {result['artist']}")
        print(f"音乐链接: {result['audio_url']}")
        
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")

if __name__ == "__main__":
    test_bgm_matching()