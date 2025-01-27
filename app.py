import streamlit as st
from simple_bgm_matcher import SimpleBGMMatcher
from PIL import Image
import os

st.title("BGM 匹配助手")

# 上传区域
uploaded_file = st.file_uploader("上传图片", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    # 显示缩略图
    st.image(uploaded_file, caption="上传的图片", width=300)

# 添加音乐类型选择
music_type = st.radio(
    "选择音乐类型",
    ["全部音乐", "纯音乐", "带歌词音乐"],
    horizontal=True
)

text_input = st.text_area("输入文案（选填）", height=100)

if uploaded_file is not None:
    match_button = st.button("开始匹配")
    
    if match_button:
        # 保存上传的图片
        temp_image_path = "temp_image.jpg"
        with open(temp_image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        with st.spinner('正在匹配BGM...'):
            matcher = SimpleBGMMatcher()
            # 传入音乐类型参数
            result = matcher.match_bgm(temp_image_path, text_input or "", music_type=music_type)
            
            if result:
                st.success("找到最佳匹配的音乐！")
                st.markdown(f"### 音乐信息")
                st.write(f"歌名：{result['name']}")
                st.write(f"艺术家：{result['artist']}")
                st.write(f"时长：{result['duration']}秒")
                st.audio(result['audio_url'])
            else:
                st.error("未找到合适的音乐，请尝试修改文案或更换图片。")
        
        os.remove(temp_image_path)

st.markdown("---")
st.markdown("提示：上传图片后点击'开始匹配'按钮，系统会为您匹配最合适的背景音乐。")