import time
from simple_bgm_matcher import SimpleContentAnalyzer

def test_image_analysis():
    analyzer = SimpleContentAnalyzer()
    
    # 测试图片路径
    image_path = "./test_image.jpg"  # 请确保这个路径指向一个真实的测试图片
    test_text = "今天天气真好"
    
    print("开始测试图像分析...")
    
    # 测试性能
    start_time = time.time()
    try:
        features = analyzer.analyze_content(image_path, test_text)
        end_time = time.time()
        
        print("\n分析结果:")
        print(f"场景识别结果: {features.get('image_scenes', [])}")
        print(f"图片亮度: {features.get('brightness', 0)}")
        print(f"处理时间: {end_time - start_time:.2f} 秒")
        
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")

if __name__ == "__main__":
    test_image_analysis()