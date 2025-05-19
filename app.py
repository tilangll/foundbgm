import streamlit as st
from simple_bgm_matcher import SimpleBGMMatcher
from PIL import Image
import os
import base64

# 获取背景图片的 base64 编码
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

bg_image = get_base64_of_bin_file('static/bg.png')
vinyl_image = get_base64_of_bin_file('static/vinyl.png')  # 获取黑胶唱片图片的 base64 编码

# 添加所有样式（将所有CSS合并到一处）
# 在文件开头保留一个统一的样式声明
if 'result' in st.session_state and st.session_state.result:
    # 匹配后增加页面内容的最大宽度
    max_width = "1200px"
else:
    # 匹配前保持之前的宽度
    max_width = "800px"

st.markdown(f"""
<style>
    /* 调整整体上边距 */
    .block-container {{
        padding-top: 1rem !important;
        max-width: {max_width};  /* 动态设置页面内容的最大宽度 */
        margin: 0 auto;  /* 居中对齐 */
    }}
    
    /* 标题样式 */
    .title-container {{
        text-align: center;
        padding: 1rem 0;
        position: relative;
        height: 200px;  /* 根据需要调整高度 */
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        background-image: url("data:image/png;base64,{bg_image}");
        background-repeat: no-repeat;
        background-position: center center;  /* 确保背景图居中 */
        background-size: contain;  /* 使用 contain 确保背景图完整展示 */
        max-width: 1000px;
        margin: 0 auto;
    }}
    
    .title-content {{
        width: 100%;
        max-width: 900px;
        text-align: center;
        display: flex;
        flex-direction: column;
        gap: 10px;
        align-items: center;
    }}

    .main-title {{
        font-size: 2.5rem;
        font-weight: bold;
        line-height: 1;
        color: black;
        margin: 0;
    }}
    
    .subtitle {{
        font-size: 16px;
        color: #111;
        line-height: 2;
        margin: 0;
    }}

    /* 自定义标题样式 */
    .stMarkdown h3 {{
        font-size: 16px !important;
        color: #111 !important;
        margin-bottom: 0rem !important;  /* 调整下方间距 */
        margin-top: 32px !important;     /* 调整上方间距 */
        line-height: 1 !important;       /* 调整行间距 */
        padding: 0 !important;           /* 将上下 padding 设置为 0 */
        font-weight: normal !important;  /* 设置字体不加粗 */
    }}
    .stMarkdown stitle {{
        font-size: 16px !important;
        color: #111 !important;
        margin-bottom: 16px !important;  /* 调整下方间距 */
        margin-top: 0px !important;     /* 调整上方间距 */
        line-height: 1 !important;       /* 调整行间距 */
        padding: 0 !important;           /* 将上下 padding 设置为 0 */
        font-weight: normal !important;  /* 设置字体不加粗 */
    }}

    /* 调整上传图片标签的间距 */
    label.st-emotion-cache-17estbc.e1dx5vew0 {{
        margin: 0 !important;  /* 将 margin 设置为 0 */
    }}

    /* 隐藏标题旁边的链接图标 */
    .stMarkdown a {{
        display: none !important;
    }}

    /* 修改单选按钮选中背景颜色 */
    div.st-ah.st-at.st-au.st-av.st-aw.st-ax.st-ay.st-ae.st-az.st-b0.st-b1.st-b2.st-b3 {{
        background-color: #1371FF !important;
    }}

    /* 修改底部提示信息的样式 */
    .footer-tip {{
        color: #666 !important;
        font-size: 14px !important;
    }}
</style>
""", unsafe_allow_html=True)

# 标题区域
st.markdown("""
<div class="title-container">
    <div class="title-content">
        <div class="main-title">一瞬</div>
        <div class="subtitle">上传画面，听见瞬间</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 提示信息，放在上传图片标题上方
if not ('result' in st.session_state and st.session_state.result):
    st.markdown('<div class="footer-tip" style="text-align: center; margin-bottom: 32px; margin-top: -16px; background-color: #F8F9FA; padding: 8px; border-radius: 5px;">提示：上传图片后点击页面最下方的"开始匹配"按钮，系统会为您匹配最合适的背景音乐。</div>', unsafe_allow_html=True)

# 上传和输入区域
if 'result' in st.session_state and st.session_state.result:
    # 匹配后使用两列布局，调整列宽比例以增加间距
    col1, _, col2 = st.columns([1, 0.1, 1])  # 使用占位符 _ 来忽略中间的列

    with col1:
        st.markdown('<div class="stMarkdown"><stitle>上传图片</stitle></div>', unsafe_allow_html=True)
        # 仅在未匹配成功时显示上传的图片缩略图
        uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None and not st.session_state.result:
            st.image(uploaded_file, caption="", width=300)

        st.markdown('<div class="stMarkdown"><h3>音乐类型</h3></div>', unsafe_allow_html=True)
        music_type = st.radio(
            "",
            ["全部音乐", "纯音乐", "带歌词音乐"],
            horizontal=True
        )

        st.markdown('<div class="stMarkdown"><h3>文案（可填）</h3></div>', unsafe_allow_html=True)
        text_input = st.text_area("", height=100)

        if uploaded_file is not None:
            # 在文件开头的样式声明中添加按钮样式
            st.markdown(f"""
            <style>
                /* 修改按钮样式 */
                .stButton>button {{
                    background-color: #1371FF !important;  /* 按钮背景色 */
                    color: white !important;  /* 按钮文字颜色 */
                    border-radius: 60px !important;  /* 按钮圆角 */
                    padding: 8px 60px !important;  /* 按钮内边距 */
                    border: none !important;  /* 去掉按钮边框 */
                    font-size: 16px !important;  /* 按钮文字大小 */
                    cursor: pointer !important;  /* 鼠标悬停时显示手型 */
                    display: block;  /* 使按钮成为块级元素 */
                    margin: 0 auto;  /* 居中对齐 */
                }}
                .stButton>button:hover {{
                    background-color: #005EEA !important;  /* 鼠标悬停时的背景色 */
                }}
            </style>
            """, unsafe_allow_html=True)

            if st.button("开始匹配"):
                temp_image_path = "temp_image.jpg"
                with open(temp_image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                with st.spinner('正在匹配BGM...'):
                    matcher = SimpleBGMMatcher()
                    result = matcher.match_bgm(temp_image_path, text_input or "", music_type=music_type)
                    if result:
                        st.session_state.has_result = True
                        st.session_state.uploaded_file = uploaded_file
                        st.session_state.music_type = music_type
                        st.session_state.text_input = text_input
                        st.session_state.result = result
                        st.rerun()
                    else:
                        st.error("未找到合适的音乐，请尝试修改文案或更换图片。")
                
                os.remove(temp_image_path)

    with col2:
        # 结果展示区域
        with col2:
            result = st.session_state.result  # 从 session_state 中获取 result
            st.markdown('<div style="margin-bottom: 24px;"><stitle>匹配结果</stitle></div>', unsafe_allow_html=True)  # 添加间距
            st.markdown(f"""
            <style>
                .result-container {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;  /* 顶部对齐 */
                    background-color: #F8F9FA;
                    padding: 16px;
                    border-radius: 8px;
                }}
                .result-info {{
                    flex: 1;
                    margin-right: 20px;
                }}
                .result-info .song-title {{
                    font-size: 24px !important;
                    font-weight: bold !important;
                    padding: 16px;
                }}
                .vinyl-container {{
                    position: relative;
                    width: 300px;  /* 黑胶唱片的宽度 */
                    height: 300px; /* 黑胶唱片的高度 */
                }}
                .vinyl-container img {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                }}
                .vinyl-container .uploaded-image {{
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    width: 100px;  /* 用户上传图片的宽度 */
                    height: 100px; /* 用户上传图片的高度 */
                    transform: translate(-50%, -50%);
                    border-radius: 50%; /* 圆形裁剪 */
                    animation: spin 8s linear infinite; /* 添加旋转动画 */
                }}
                @keyframes spin {{
                    from {{ transform: translate(-50%, -50%) rotate(0deg); }}
                    to {{ transform: translate(-50%, -50%) rotate(360deg); }}
                }}
                .audio-player {{
                    margin-top: 16px;  /* 添加顶部间距 */
                    width: 100%;  /* 使音频播放器占满可用宽度 */
                }}
            </style>
            <div class="result-container">
                <div class="result-info">
                    <h3 class="song-title">{result['name']}</h3>
                    <p>{result['artist']}</p>
                    <p>{result['duration']} 秒</p>
                </div>
                <div class="vinyl-container">
                    <img src="data:image/png;base64,{vinyl_image}" alt="Vinyl">
                    <img class="uploaded-image" src="data:image/png;base64,{base64.b64encode(uploaded_file.getbuffer()).decode()}" alt="Uploaded Image">
                </div>
            </div>
            <audio class="audio-player" controls>
                <source src="{result['audio_url']}" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
            """, unsafe_allow_html=True)
else:
    # 匹配前保持整体居中
    st.markdown('<div class="stMarkdown"><stitle>上传图片</stitle></div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        st.image(uploaded_file, caption="", width=300)

    st.markdown('<div class="stMarkdown"><h3>音乐类型</h3></div>', unsafe_allow_html=True)
    music_type = st.radio(
        "",
        ["全部音乐", "纯音乐", "带歌词音乐"],
        horizontal=True
    )

    st.markdown('<div class="stMarkdown"><h3>文案（可填）</h3></div>', unsafe_allow_html=True)
    text_input = st.text_area("", height=100)

    if uploaded_file is not None:
        # 在文件开头的样式声明中添加按钮样式
        st.markdown(f"""
        <style>
            /* 修改按钮样式 */
            .stButton>button {{
                background-color: #1371FF !important;  /* 按钮背景色 */
                color: white !important;  /* 按钮文字颜色 */
                border-radius: 60px !important;  /* 按钮圆角 */
                padding: 8px 60px !important;  /* 按钮内边距 */
                border: none !important;  /* 去掉按钮边框 */
                font-size: 16px !important;  /* 按钮文字大小 */
                cursor: pointer !important;  /* 鼠标悬停时显示手型 */
                display: block;  /* 使按钮成为块级元素 */
                margin: 0 auto;  /* 居中对齐 */
            }}
            .stButton>button:hover {{
                background-color: #005EEA !important;  /* 鼠标悬停时的背景色 */
            }}
        </style>
        """, unsafe_allow_html=True)

        if st.button("开始匹配"):
            temp_image_path = "temp_image.jpg"
            with open(temp_image_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            with st.spinner('正在匹配BGM...'):
                matcher = SimpleBGMMatcher()
                result = matcher.match_bgm(temp_image_path, text_input or "", music_type=music_type)
                if result:
                    st.session_state.has_result = True
                    st.session_state.uploaded_file = uploaded_file
                    st.session_state.music_type = music_type
                    st.session_state.text_input = text_input
                    st.session_state.result = result
                    st.rerun()
                else:
                    st.error("未找到合适的音乐，请尝试修改文案或更换图片。")
            
            os.remove(temp_image_path)