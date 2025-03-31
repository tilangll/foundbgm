from PIL import Image
import numpy as np

# 创建一个简单的测试图片
img = Image.new('RGB', (300, 300), color='white')
img.save('test_image.jpg')