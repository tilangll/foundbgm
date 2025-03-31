import os
import streamlit as st

try:
    # 尝试从 Streamlit Secrets 获取
    NETEASE_PHONE = st.secrets["NETEASE_PHONE"]
    NETEASE_PASSWORD = st.secrets["NETEASE_PASSWORD"]
except Exception:
    try:
        # 尝试从环境变量获取
        NETEASE_PHONE = os.environ["NETEASE_PHONE"]
        NETEASE_PASSWORD = os.environ["NETEASE_PASSWORD"]
    except KeyError:
        # 如果都没有，使用默认值（仅用于本地开发）
        NETEASE_PHONE = "18666521665"
        NETEASE_PASSWORD = "tianlunAee1！"