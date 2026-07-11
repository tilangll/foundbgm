import base64
import html
import json
import os
import time

import streamlit as st
from streamlit.components.v1 import html as components_html

from simple_bgm_matcher import SimpleBGMMatcher


st.set_page_config(page_title="一瞬", page_icon="♪", layout="wide")

MATCHER_CACHE_VERSION = "internet-archive-v2"


@st.cache_resource(show_spinner=False)
def get_matcher(cache_version: str):
    return SimpleBGMMatcher()


def get_base64_of_bin_file(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def encode_bytes(data: bytes) -> str:
    return base64.b64encode(data).decode()


VINYL_IMAGE = get_base64_of_bin_file("static/vinyl.png")


def init_state():
    defaults = {
        "view": "home",
        "result": None,
        "uploaded_image_bytes": None,
        "uploaded_image_mime": "image/jpeg",
        "uploaded_image_name": "",
        "music_type": "带歌词音乐",
        "text_input": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def inject_styles():
    st.markdown(
        """
<style>
    :root {
        --bg: #050814;
        --bg-soft: #0d1320;
        --panel: rgba(255, 255, 255, 0.05);
        --panel-border: rgba(255, 255, 255, 0.08);
        --text: #f7f8fb;
        --muted: rgba(247, 248, 251, 0.58);
        --accent: #8ab0ff;
        --accent-strong: #0f43ff;
        --control-bg: rgba(255, 255, 255, 0.055);
        --control-border: rgba(255, 255, 255, 0.14);
    }

    .stApp {
        min-height: 100vh;
        background:
            radial-gradient(circle at 12% 18%, rgba(50, 97, 255, 0.22), transparent 20%),
            radial-gradient(circle at 78% 12%, rgba(128, 181, 255, 0.12), transparent 18%),
            linear-gradient(180deg, #07101d 0%, #04070d 100%);
    }

    header[data-testid="stHeader"],
    [data-testid="stToolbar"],
    #MainMenu,
    footer {
        display: none !important;
    }

    .block-container {
        max-width: 1440px !important;
        padding: clamp(1.5rem, 4vh, 3.8rem) clamp(1.2rem, 4vw, 4.8rem) 3rem !important;
    }

    .stMarkdown a {
        display: none !important;
    }

    .home-shell {
        min-height: calc(100vh - 5rem);
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        color: var(--text);
        padding-top: 0;
    }

    .brand {
        color: var(--accent);
        font-size: 0.96rem;
        font-weight: 500;
        letter-spacing: 0.24em;
        text-transform: uppercase;
        margin-bottom: 2.2rem;
        opacity: 0.9;
    }

    .home-title {
        font-size: clamp(4.8rem, 8.5vw, 9rem);
        line-height: 0.92;
        letter-spacing: -0.09em;
        font-weight: 850;
        margin: 0;
        white-space: nowrap;
    }

    .home-subline {
        margin-top: 1.35rem;
        max-width: 26rem;
        color: var(--muted);
        font-size: 0.96rem;
        line-height: 1.9;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .home-layout {
        display: grid;
        grid-template-columns: minmax(0, 0.86fr) minmax(380px, 1.14fr);
        align-items: center;
        gap: clamp(2rem, 7vw, 8rem);
        min-height: calc(100vh - 8.5rem);
    }

    .home-hero {
        padding-bottom: 2rem;
    }

    .hero-index {
        display: inline-flex;
        align-items: center;
        gap: 0.8rem;
        margin-top: 3.5rem;
        color: rgba(247, 248, 251, 0.42);
        font-size: 0.72rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
    }

    .hero-index::before {
        content: "";
        width: 2.4rem;
        height: 1px;
        background: rgba(138, 176, 255, 0.7);
    }

    .st-key-input-panel {
        padding: clamp(1.35rem, 3vw, 2.2rem) !important;
        border-radius: 32px;
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.025)),
            linear-gradient(135deg, rgba(24, 38, 71, 0.46), rgba(8, 12, 22, 0.72));
        border: 1px solid var(--panel-border);
        backdrop-filter: blur(22px);
        box-shadow:
            0 30px 90px rgba(0, 0, 0, 0.34),
            inset 0 1px 0 rgba(255, 255, 255, 0.05);
    }

    .input-panel-heading {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 1rem;
        margin-bottom: 1.35rem;
    }

    .section-label {
        color: var(--muted);
        font-size: 0.82rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        margin-bottom: 1.1rem;
        font-weight: 400;
    }

    .input-panel-note {
        color: rgba(247, 248, 251, 0.32);
        font-size: 0.7rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }

    .stFileUploader > label,
    .stRadio > label,
    .stTextArea > label {
        color: rgba(247, 248, 251, 0.92) !important;
        font-size: 0.98rem !important;
        font-weight: 400 !important;
        letter-spacing: 0.02em !important;
    }

    .stFileUploader [data-testid="stTooltipIcon"] svg {
        color: #ffffff !important;
        stroke: #ffffff !important;
    }

    .stFileUploader section {
        border-radius: 26px !important;
        border: 1px dashed var(--control-border) !important;
        background: var(--control-bg) !important;
    }

    .stFileUploader {
        margin-bottom: 1.15rem !important;
    }

    .stFileUploader [data-testid="stTooltipIcon"] {
        display: none !important;
    }

    [data-testid="stFileUploaderDropzoneInstructions"] > div,
    [data-testid="stFileUploaderDropzoneInstructions"] small {
        color: rgba(247, 248, 251, 0.62) !important;
    }

    [data-testid="stFileUploaderDropzone"] button {
        color: #f8fbff !important;
        background: rgba(30, 75, 210, 0.72) !important;
        border-color: rgba(138, 176, 255, 0.24) !important;
    }

    .stFileUploader div:has(> ul > li > [data-testid="stFileUploaderFile"]) {
        padding-left: 0 !important;
        padding-right: 0 !important;
    }

    [data-testid="stFileUploaderFile"] {
        display: flex !important;
        align-items: center !important;
        gap: 0.75rem !important;
        min-height: 58px !important;
        padding: 0.65rem 0.85rem !important;
        margin-top: 0.75rem !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
        background: var(--control-bg) !important;
        border: 1px solid var(--control-border) !important;
        border-radius: 18px !important;
    }

    [data-testid="stFileUploaderFile"] > div:first-child {
        display: flex !important;
        flex: 0 0 2.2rem !important;
        align-items: center !important;
        justify-content: center !important;
        color: rgba(255, 255, 255, 0.82) !important;
    }

    [data-testid="stFileUploaderFile"] > div:first-child svg {
        width: 1.8rem !important;
        height: 1.8rem !important;
    }

    [data-testid="stFileUploaderFileData"] {
        display: flex !important;
        min-width: 0 !important;
        flex: 1 1 auto !important;
        align-items: baseline !important;
        gap: 0.55rem !important;
    }

    [data-testid="stFileUploaderFileName"] {
        min-width: 0 !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
        color: #ffffff !important;
        font-size: 0.98rem !important;
        font-weight: 500 !important;
    }

    [data-testid="stFileUploaderFileData"] > div,
    [data-testid="stFileUploaderFileData"] > span {
        color: rgba(255, 255, 255, 0.56) !important;
        font-size: 0.84rem !important;
        white-space: nowrap !important;
    }

    [data-testid="stFileUploaderDeleteBtn"] {
        flex: 0 0 auto !important;
    }

    [data-testid="stFileUploaderDeleteBtn"] button {
        min-width: 2rem !important;
        min-height: 2rem !important;
        padding: 0.25rem !important;
        color: rgba(255, 255, 255, 0.68) !important;
        background: transparent !important;
        border: none !important;
    }

    [data-testid="stFileUploaderFile"] svg,
    [data-testid="stFileUploaderDeleteBtn"] {
        color: rgba(255, 255, 255, 0.78) !important;
        fill: currentColor !important;
    }

    .stTextArea [data-testid="stTextAreaRootElement"],
    .stTextArea [data-baseweb="textarea"],
    .stTextArea [data-baseweb="base-input"] {
        background: var(--control-bg) !important;
        border: 1px solid var(--control-border) !important;
        box-shadow: none !important;
        border-radius: 22px !important;
    }

    .stTextArea textarea {
        min-height: 118px !important;
        border-radius: 22px !important;
        background: transparent !important;
        color: #ffffff !important;
        caret-color: #ffffff !important;
        border: none !important;
    }

    .stTextArea textarea::placeholder {
        color: rgba(255, 255, 255, 0.56) !important;
        opacity: 1 !important;
    }

    .stTextArea {
        margin-top: 1.15rem !important;
    }

    .stRadio [role="radiogroup"] {
        gap: 0.55rem;
    }

    .stRadio {
        margin-top: 1.15rem !important;
        margin-bottom: 1.15rem !important;
    }

    .stRadio [data-baseweb="radio"] {
        padding: 0.48rem 1rem;
        border-radius: 999px;
        background: var(--control-bg) !important;
        border: 1px solid var(--control-border) !important;
    }

    .stRadio [data-baseweb="radio"] [data-testid="stMarkdownContainer"] p,
    .stRadio [data-baseweb="radio"] {
        color: #ffffff !important;
    }

    .stButton > button {
        width: 100%;
        min-height: 58px;
        border-radius: 999px !important;
        border: none !important;
        background: linear-gradient(135deg, #0c35d6 0%, #1854ff 48%, #6ea6ff 100%) !important;
        color: #f8fbff !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        box-shadow:
            0 22px 50px rgba(18, 74, 255, 0.42),
            inset 0 1px 0 rgba(255, 255, 255, 0.18);
    }

    .stButton > button:hover {
        filter: brightness(1.08);
    }

    .st-key-result-back {
        position: fixed !important;
        top: 1.35rem;
        right: 1.5rem;
        z-index: 50;
        width: auto !important;
    }

    .st-key-result-back .stButton > button {
        width: auto !important;
        min-height: 40px;
        padding: 0 1rem;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        background: rgba(7, 10, 16, 0.34) !important;
        color: rgba(255, 255, 255, 0.9) !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.05em !important;
        text-transform: none !important;
        box-shadow: none !important;
        backdrop-filter: blur(14px);
    }

    .st-key-result-view {
        position: fixed !important;
        inset: 0 !important;
        z-index: 20 !important;
        width: 100vw !important;
        height: 100vh !important;
        max-width: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    .st-key-result-view iframe,
    .st-key-result-view [data-testid="stIFrame"] {
        display: block !important;
        width: 100vw !important;
        height: 100vh !important;
        min-height: 720px !important;
        border: 0 !important;
    }

    .progress-shell {
        margin-top: 1rem;
        color: var(--muted);
        font-size: 0.95rem;
    }

    .result-screen {
        position: fixed;
        inset: 0;
        width: 100vw;
        height: 100vh;
        margin-left: calc(50% - 50vw);
        background-size: contain;
        background-position: center center;
        background-repeat: no-repeat;
        background-color: #05070c;
        overflow: hidden;
    }

    .result-screen::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
            linear-gradient(180deg, rgba(5, 7, 12, 0.18) 0%, rgba(5, 7, 12, 0.68) 100%),
            radial-gradient(circle at center, rgba(255, 255, 255, 0.06), transparent 42%);
        backdrop-filter: blur(4px);
    }

    .result-inner {
        position: relative;
        z-index: 2;
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 3rem 1.5rem;
        color: white;
        text-align: center;
    }

    .result-top {
        position: absolute;
        top: 1.5rem;
        left: 1.5rem;
        right: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    }

    .result-brand {
        color: rgba(255, 255, 255, 0.76);
        font-size: 0.95rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
    }

    .ghost-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 40px;
        padding: 0 1rem;
        border-radius: 999px;
        color: white;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.14);
        backdrop-filter: blur(12px);
    }

    .record-wrap {
        position: relative;
        width: min(40vw, 360px);
        height: min(40vw, 360px);
        min-width: 220px;
        min-height: 220px;
        margin-bottom: 2rem;
        animation: spin 12s linear infinite;
        filter: drop-shadow(0 24px 36px rgba(0, 0, 0, 0.36));
    }

    .record-wrap img {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
    }

    .record-center {
        position: absolute;
        top: 50%;
        left: 50%;
        width: 36%;
        height: 36%;
        transform: translate(-50%, -50%);
        border-radius: 50%;
        overflow: hidden;
        background-position: center;
        background-size: cover;
        box-shadow:
            0 0 0 10px rgba(0, 0, 0, 0.18),
            inset 0 0 0 1px rgba(255, 255, 255, 0.14);
    }

    .song-name {
        font-size: clamp(2.2rem, 4vw, 3.3rem);
        line-height: 1.02;
        font-weight: 800;
        letter-spacing: -0.05em;
        margin-bottom: 0.75rem;
    }

    .song-sub {
        color: rgba(255, 255, 255, 0.8);
        font-size: 1.15rem;
        margin-bottom: 1.4rem;
    }

    .meta-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(90px, 1fr));
        gap: 0.8rem;
        width: min(760px, 100%);
        margin: 0 auto 1.4rem;
    }

    .meta-card {
        padding: 0.95rem 0.8rem;
        border-radius: 20px;
        background: rgba(7, 10, 16, 0.28);
        border: 1px solid rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(12px);
    }

    .meta-label {
        color: rgba(255, 255, 255, 0.62);
        font-size: 0.82rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
    }

    .meta-value {
        color: white;
        font-size: 0.98rem;
        line-height: 1.4;
        word-break: break-word;
    }

    .audio-panel {
        width: min(760px, 100%);
        padding: 1rem 1.05rem;
        border-radius: 24px;
        background: rgba(7, 10, 16, 0.28);
        border: 1px solid rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(12px);
    }

    .audio-panel audio {
        width: 100%;
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    @media (max-width: 900px) {
        .block-container {
            max-width: 100% !important;
            padding-top: 1.25rem !important;
        }

        .home-layout {
            grid-template-columns: 1fr;
            gap: 2rem;
            min-height: auto;
        }

        .home-title {
            font-size: 4.8rem;
        }

        .home-hero {
            padding-bottom: 0;
        }

        .hero-index {
            margin-top: 2rem;
        }

        .meta-grid {
            grid-template-columns: repeat(2, minmax(120px, 1fr));
        }

        .result-top {
            top: 1rem;
            left: 1rem;
            right: 1rem;
        }
    }
</style>
        """,
        unsafe_allow_html=True,
    )


def save_uploaded_file(uploaded_file):
    image_bytes = uploaded_file.getvalue()
    st.session_state.uploaded_image_bytes = image_bytes
    st.session_state.uploaded_image_mime = uploaded_file.type or "image/jpeg"
    st.session_state.uploaded_image_name = uploaded_file.name
    return image_bytes


def reset_to_home():
    st.session_state.view = "home"
    st.session_state.result = None
    st.session_state.music_type = "带歌词音乐"


def format_duration(value) -> str:
    try:
        seconds = max(0, int(float(value or 0)))
    except (TypeError, ValueError):
        return "未知"

    if not seconds:
        return "未知"
    if seconds >= 3600:
        return f"{seconds // 3600}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def run_match(uploaded_file, music_type: str, text_input: str):
    if uploaded_file is None:
        st.error("请先上传一张图片。")
        return

    image_bytes = save_uploaded_file(uploaded_file)
    st.session_state.music_type = music_type
    st.session_state.text_input = text_input

    temp_image_path = "temp_image.jpg"
    with open(temp_image_path, "wb") as f:
        f.write(image_bytes)

    progress = st.progress(0)
    status = st.empty()

    try:
        status.markdown('<div class="progress-shell">正在读取画面...</div>', unsafe_allow_html=True)
        progress.progress(12)
        time.sleep(0.15)

        status.markdown('<div class="progress-shell">正在分析情绪和画面氛围...</div>', unsafe_allow_html=True)
        progress.progress(38)
        time.sleep(0.15)

        status.markdown('<div class="progress-shell">正在搜索最合适的背景音乐...</div>', unsafe_allow_html=True)
        matcher = get_matcher(MATCHER_CACHE_VERSION)
        result = matcher.match_bgm(temp_image_path, text_input or "", music_type=music_type)
        progress.progress(78)

        if result:
            st.session_state.result = result
            st.session_state.view = "result"
            status.markdown('<div class="progress-shell">匹配成功，正在生成结果页...</div>', unsafe_allow_html=True)
            progress.progress(100)
            time.sleep(0.2)
            st.rerun()

        st.error(matcher.last_error or "未找到合适的音乐，请尝试修改文案或更换图片。")
    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)


def render_home():
    left, right = st.columns([0.86, 1.14], gap="large")

    with left:
        st.markdown(
            """
            <div class="home-shell home-hero">
                <div class="brand">YI SHUN / SCENE BGM</div>
                <h1 class="home-title">上传画面<br>听见瞬间</h1>
                <div class="home-subline">Image to mood. Scene to sound.</div>
                <div class="hero-index">01 / Upload your scene</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        with st.container(key="input-panel"):
            st.markdown(
                """
                <div class="input-panel-heading">
                    <div class="section-label">Scene Input</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            uploaded_file = st.file_uploader(
                "上传图片",
                type=["jpg", "jpeg", "png"],
                help="支持 JPG / JPEG / PNG",
            )

            music_type = st.radio(
                "音乐类型",
                ["全部音乐", "纯音乐", "带歌词音乐"],
                index=["全部音乐", "纯音乐", "带歌词音乐"].index(st.session_state.music_type),
                horizontal=True,
            )

            text_input = st.text_area(
                "文案（可填）",
                value=st.session_state.text_input,
                placeholder="例如：雪夜便利店吃关东煮，耳机突然灌进橘子海的英伦浪花",
            )

            if st.button("开始匹配"):
                run_match(uploaded_file, music_type, text_input)


def render_result():
    image_b64 = encode_bytes(st.session_state.uploaded_image_bytes)
    image_mime = html.escape(st.session_state.uploaded_image_mime or "image/jpeg", quote=True)
    cover_image = f"url('data:{image_mime};base64,{image_b64}')"
    result = st.session_state.result or {}

    def safe_text(key: str, fallback: str) -> str:
        value = result.get(key) or fallback
        return html.escape(str(value))

    lyricist = safe_text("lyricist", "未知")
    composer = safe_text("composer", "未知")
    artist = safe_text("artist", "未知艺术家")
    name = safe_text("name", "未命名歌曲")
    audio_mime_type = html.escape(str(result.get("audio_mime_type") or "audio/mpeg"), quote=True)
    raw_audio_urls = result.get("audio_urls") or [result.get("audio_url")]
    audio_urls = []
    for url in raw_audio_urls:
        if url and url not in audio_urls:
            audio_urls.append(str(url))
    audio_sources = [
        {"url": html.escape(url, quote=True), "type": audio_mime_type}
        for url in audio_urls
    ]
    audio_sources_html = "\n".join(
        f'<source src="{source["url"]}" type="{source["type"]}">'
        for source in audio_sources
    )
    audio_sources_js = json.dumps(
        [
            {"url": url, "type": str(result.get("audio_mime_type") or "audio/mpeg")}
            for url in audio_urls
        ],
        ensure_ascii=False,
    )
    duration = format_duration(result.get("duration"))

    result_css = """
        * { box-sizing: border-box; }
        html, body {
            margin: 0;
            width: 100%;
            min-height: 100%;
            overflow: hidden;
            background: #05070c;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
        }
        .result-screen {
            position: relative;
            width: 100%;
            height: 100vh;
            min-height: 720px;
            overflow: hidden;
            background-color: #05070c;
            background-position: center;
            background-repeat: no-repeat;
            background-size: contain;
        }
        .result-screen::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(180deg, rgba(5, 7, 12, 0.16), rgba(5, 7, 12, 0.72)),
                radial-gradient(circle at center, rgba(255, 255, 255, 0.08), transparent 42%);
            backdrop-filter: blur(4px);
        }
        .result-inner {
            position: relative;
            z-index: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            padding: 3rem 1.5rem;
            text-align: center;
        }
        .result-top {
            position: absolute;
            top: 1.5rem;
            left: 1.5rem;
            right: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
        }
        .result-brand {
            color: rgba(255, 255, 255, 0.78);
            font-size: 0.8rem;
            letter-spacing: 0.2em;
            text-transform: uppercase;
        }
        .ghost-button {
            display: inline-flex;
            align-items: center;
            min-height: 38px;
            padding: 0 0.9rem;
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 999px;
            color: rgba(255, 255, 255, 0.86);
            background: rgba(7, 10, 16, 0.34);
            backdrop-filter: blur(12px);
            font-size: 0.72rem;
            letter-spacing: 0.08em;
        }
        .record-wrap {
            position: relative;
            width: clamp(220px, 34vmin, 360px);
            aspect-ratio: 1 / 1;
            flex: 0 0 auto;
            margin-bottom: 1.75rem;
            filter: drop-shadow(0 24px 36px rgba(0, 0, 0, 0.38));
            animation: spin 12s linear infinite;
        }
        .record-wrap.is-paused { animation-play-state: paused; }
        .record-wrap > img {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            display: block;
            object-fit: contain;
        }
        .record-center {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 36%;
            aspect-ratio: 1 / 1;
            transform: translate(-50%, -50%);
            border-radius: 50%;
            overflow: hidden;
            background-position: center;
            background-size: cover;
            box-shadow:
                0 0 0 10px rgba(0, 0, 0, 0.18),
                inset 0 0 0 1px rgba(255, 255, 255, 0.14);
        }
        .song-name {
            max-width: min(760px, 92vw);
            color: #ffffff;
            font-size: clamp(2rem, 4vw, 3.3rem);
            font-weight: 800;
            line-height: 1.05;
            letter-spacing: -0.05em;
        }
        .song-sub {
            margin-top: 0.65rem;
            margin-bottom: 1.25rem;
            color: rgba(255, 255, 255, 0.8);
            font-size: 1.05rem;
        }
        .meta-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(92px, 1fr));
            gap: 0.75rem;
            width: min(760px, 100%);
            margin-bottom: 1rem;
        }
        .meta-card {
            padding: 0.8rem 0.7rem;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 18px;
            background: rgba(7, 10, 16, 0.3);
            backdrop-filter: blur(12px);
        }
        .meta-label {
            margin-bottom: 0.35rem;
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.7rem;
            letter-spacing: 0.1em;
        }
        .meta-value {
            overflow: hidden;
            color: #ffffff;
            font-size: 0.9rem;
            line-height: 1.35;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .audio-panel {
            width: min(760px, 100%);
            padding: 0.85rem 1rem 0.7rem;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 22px;
            background: rgba(7, 10, 16, 0.32);
            backdrop-filter: blur(12px);
        }
        .player-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.55rem;
            color: rgba(255, 255, 255, 0.62);
            font-size: 0.7rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }
        .play-toggle {
            padding: 0.35rem 0.8rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 999px;
            color: #ffffff;
            background: rgba(255, 255, 255, 0.1);
            cursor: pointer;
        }
        audio { display: block; width: 100%; }
        .audio-status {
            min-height: 1.05rem;
            margin-top: 0.42rem;
            color: rgba(255, 255, 255, 0.5);
            font-size: 0.68rem;
            letter-spacing: 0.04em;
        }
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        @media (max-width: 700px) {
            .result-inner { padding: 2.5rem 1rem 1.5rem; }
            .result-top { top: 0.9rem; left: 0.9rem; right: 0.9rem; }
            .result-brand { font-size: 0.65rem; }
            .ghost-button { display: none; }
            .record-wrap { width: min(62vmin, 300px); }
            .meta-grid { grid-template-columns: repeat(2, minmax(100px, 1fr)); }
        }
    """
    result_html = f"""
        <!doctype html>
        <html lang="zh-CN">
        <head><meta charset="utf-8"><style>{result_css}</style></head>
        <body>
            <div class="result-screen" style="background-image: {cover_image};">
                <div class="result-inner">
                    <div class="result-top">
                        <div class="result-brand">YI SHUN / NOW PLAYING</div>
                    </div>

                    <div class="record-wrap">
                        <img src="data:image/png;base64,{VINYL_IMAGE}" alt="vinyl" />
                        <div class="record-center" style="background-image: {cover_image};"></div>
                    </div>

                    <div class="song-name">{name}</div>
                    <div class="song-sub">{artist}</div>

                    <div class="meta-grid">
                        <div class="meta-card"><div class="meta-label">作词</div><div class="meta-value">{lyricist}</div></div>
                        <div class="meta-card"><div class="meta-label">作曲</div><div class="meta-value">{composer}</div></div>
                        <div class="meta-card"><div class="meta-label">歌手</div><div class="meta-value">{artist}</div></div>
                        <div class="meta-card"><div class="meta-label">时长</div><div class="meta-value">{duration}</div></div>
                    </div>

                    <div class="audio-panel">
                        <div class="player-head"><span>NOW PLAYING</span><button class="play-toggle" id="play-toggle" type="button">播放音乐</button></div>
                        <audio id="audio" controls preload="auto">{audio_sources_html}</audio>
                        <div class="audio-status" id="audio-status"></div>
                    </div>
                </div>
            </div>
            <script>
                const audio = document.getElementById("audio");
                const toggle = document.getElementById("play-toggle");
                const record = document.querySelector(".record-wrap");
                const status = document.getElementById("audio-status");
                const sources = {audio_sources_js};
                let sourceIndex = 0;
                let userRequestedPlay = false;

                const setStatus = (message) => {{
                    status.textContent = message || "";
                }};
                const sync = () => {{
                    const buffering = userRequestedPlay && !audio.paused && audio.readyState < 3;
                    toggle.textContent = audio.paused ? "播放音乐" : (buffering ? "加载中..." : "暂停播放");
                    record.classList.toggle("is-paused", audio.paused || buffering);
                }};
                const loadSource = (index, shouldPlay = false) => {{
                    if (!sources[index]) {{
                        setStatus("暂无可播放音频源，返回后再匹配一首试试。");
                        sync();
                        return;
                    }}
                    sourceIndex = index;
                    audio.src = sources[sourceIndex].url;
                    audio.load();
                    setStatus("音频正在从 Internet Archive 加载，可能需要几秒。");
                    if (shouldPlay) {{
                        sync();
                        audio.play().catch(() => {{
                            setStatus("浏览器拦截了自动播放，请再点一次播放。");
                            sync();
                        }});
                    }}
                }};
                toggle.addEventListener("click", () => {{
                    if (audio.paused) {{
                        userRequestedPlay = true;
                        if (!audio.currentSrc && sources.length) {{
                            loadSource(sourceIndex, true);
                        }} else {{
                            setStatus("正在请求音频，网络慢时会多等几秒。");
                            sync();
                            audio.play().catch(() => {{
                                setStatus("浏览器拦截了自动播放，请再点一次播放。");
                                sync();
                            }});
                        }}
                    }} else {{
                        audio.pause();
                    }}
                }});
                audio.addEventListener("loadstart", () => {{
                    if (!userRequestedPlay) setStatus("音频正在从 Internet Archive 加载，可能需要几秒。");
                    sync();
                }});
                audio.addEventListener("loadedmetadata", () => {{
                    if (!userRequestedPlay) setStatus("音频已找到，点击播放音乐。");
                    sync();
                }});
                audio.addEventListener("canplay", () => {{
                    if (!userRequestedPlay) setStatus("音频已就绪，点击播放音乐。");
                    sync();
                }});
                audio.addEventListener("waiting", () => {{
                    setStatus("音频正在缓冲，网络慢时会多等几秒。");
                    sync();
                }});
                audio.addEventListener("stalled", () => {{
                    setStatus("音频加载较慢，正在继续尝试...");
                    sync();
                }});
                audio.addEventListener("error", () => {{
                    if (sourceIndex + 1 < sources.length) {{
                        loadSource(sourceIndex + 1, userRequestedPlay);
                        return;
                    }}
                    setStatus("音频源加载失败，返回后再匹配一首试试。");
                    sync();
                }});
                audio.addEventListener("play", sync);
                audio.addEventListener("playing", () => {{
                    setStatus("");
                    sync();
                }});
                audio.addEventListener("pause", sync);
                audio.addEventListener("ended", sync);
                loadSource(0, false);
                sync();
            </script>
        </body>
        </html>
    """
    with st.container(key="result-view"):
        components_html(result_html, height=1000, scrolling=False)

    with st.container(key="result-back"):
        if st.button("返回上传页", key="result-back-button"):
            reset_to_home()
            st.rerun()


init_state()
inject_styles()

if st.session_state.view == "result" and st.session_state.uploaded_image_bytes and st.session_state.result:
    render_result()
else:
    render_home()
