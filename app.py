import streamlit as st
from simple_bgm_matcher import SimpleBGMMatcher
from PIL import Image
import os

st.title("BGM 匹配助手")

# 文件上传区域
uploaded_file = st.file_uploader("上传图片", type=["jpg", "jpeg", "png"])
text_input = st.text_area("输入文案", height=100)

if uploaded_file is not None and text_input:
    # 保存上传的图片
    temp_image_path = "temp_image.jpg"
    with open(temp_image_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # 显示上传的图片
    st.image(uploaded_file, caption="上传的图片", use_column_width=True)
    
    # 匹配音乐
    matcher = SimpleBGMMatcher()
    result = matcher.match_bgm(temp_image_path, text_input)
    
    if result:
        st.success("找到最佳匹配的音乐！")
        st.markdown(f"### 音乐信息")
        st.write(f"歌名：{result['name']}")
        st.write(f"艺术家：{result['artist']}")
        st.write(f"时长：{result['duration']}秒")
        
        # 添加音乐链接
        st.markdown(f"[点击这里试听音乐]({result['audio_url']})")
        
        # 显示版权信息
        st.markdown(f"[查看许可证信息]({result['license']})")
    else:
        st.error("未找到合适的音乐，请尝试修改文案或更换图片。")
    
    # 清理临时文件
    os.remove(temp_image_path)

st.markdown("---")
st.markdown("提示：上传图片并输入文案后，系统会自动为您匹配最合适的背景音乐。")