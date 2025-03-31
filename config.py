import os
import streamlit as st

# 优先使用 Streamlit Secrets，然后是环境变量
NETEASE_PHONE = st.secrets.get("NETEASE_PHONE", os.getenv('NETEASE_PHONE'))
NETEASE_PASSWORD = st.secrets.get("NETEASE_PASSWORD", os.getenv('NETEASE_PASSWORD'))

if not NETEASE_PHONE or not NETEASE_PASSWORD:
    raise ValueError("请在 Streamlit Secrets 或环境变量中设置 NETEASE_PHONE 和 NETEASE_PASSWORD")