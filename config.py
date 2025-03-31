# Use environment variables or secure storage in production
import os

NETEASE_PHONE = os.getenv('NETEASE_PHONE')
NETEASE_PASSWORD = os.getenv('NETEASE_PASSWORD')

if not NETEASE_PHONE or not NETEASE_PASSWORD:
    raise ValueError("请设置环境变量 NETEASE_PHONE 和 NETEASE_PASSWORD")