from simple_bgm_matcher import SimpleBGMMatcher
import os

def test_bgm_matching():
    # 测试图片路径
    image_path = "test_images/test.jpg"
    
    # 测试文本
    test_text = "美丽典雅的紫色手织老布，纹理真漂亮迷人😍"
    
    # 创建匹配器实例
    matcher = SimpleBGMMatcher()
    
    print("开始BGM匹配...")
    print(f"分析图片: {image_path}")
    print(f"分析文本: {test_text}")
    
    # 执行匹配
    result = matcher.match_bgm(image_path, test_text)
    
    if result:
        print("\n=== 匹配结果 ===")
        print(f"歌曲名称: {result['name']}")
        print(f"艺术家: {result['artist']}")
        print(f"时长: {result['duration']}秒")
        print(f"音乐链接: {result['audio_url']}")
        print(f"许可证: {result['license']}")
        print(f"情感标签: {', '.join(result['mood_tags'])}")
    else:
        print("未找到匹配的BGM")

if __name__ == "__main__":
    test_bgm_matching()