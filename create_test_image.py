from PIL import Image
import numpy as np

# 创建一个简单的测试图片
img = Image.fromarray(np.random.randint(0, 255, (300, 300, 3), dtype=np.uint8))
img.save('test_image.jpg')