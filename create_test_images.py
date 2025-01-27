from PIL import Image
import os

# 创建目录
os.makedirs('test_images', exist_ok=True)

# 创建纯色图片
def create_solid_image(color, filename):
    img = Image.new('RGB', (100, 100), color)
    img.save(f'test_images/{filename}')

# 创建三张测试图片
create_solid_image((255, 255, 200), 'happy.jpg')    # 明亮的黄色
create_solid_image((50, 50, 80), 'sad.jpg')         # 深蓝色
create_solid_image((150, 150, 150), 'neutral.jpg')  # 灰色