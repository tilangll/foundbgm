import time
from simple_bgm_matcher import SimpleContentAnalyzer
from PIL import Image
import numpy as np
import os

def test_performance(image_path: str, text: str, iterations: int = 5):
    print("初始化模型...")
    analyzer = SimpleContentAnalyzer()
    
    # 确保测试图片存在
    if not os.path.exists(image_path):
        print(f"创建测试图片: {image_path}")
        img = Image.new('RGB', (300, 300), color='white')
        img.save(image_path)
    
    print("\n开始测试...")
    total_time = 0
    for i in range(iterations):
        start_time = time.time()
        features = analyzer.analyze_content(image_path, text)
        end_time = time.time()
        total_time += (end_time - start_time)
        print(f"第 {i+1} 次分析用时: {end_time - start_time:.2f} 秒")
        print(f"特征值: {features}")
    
    print(f"\n平均分析时间: {total_time/iterations:.2f} 秒")

if __name__ == "__main__":
    test_image = os.path.join(os.path.dirname(__file__), "test_image.jpg")
    test_text = "这是一段测试文本，用于测试情感分析性能"
    
    print("开始性能测试...")
    test_performance(test_image, test_text)