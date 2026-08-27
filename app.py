"""
700 單字英文學習與測驗 Web App (700 English Vocabulary Master)
Main Streamlit Application Entry Point.
"""

import os
import streamlit as st
import pandas as pd
import json

from utils.data_loader import (
    load_default_vocab,
    parse_uploaded_file,
    get_unit_words,
    get_total_units,
    search_vocabulary
)
from components.flashcard import render_flashcard_view, render_word_list_view
from components.quiz_engine import render_quiz_view
from components.progress_tracker import init_progress_state, render_dashboard, render_user_switcher_sidebar, update_last_reading_position
from components.audio_player import render_speech_button
from components.word_bank import render_word_bank_page

# Streamlit Page Config
st.set_page_config(
    page_title="700 單字英文學習與測驗 Web App",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS Styling
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "styles", "custom.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()
init_progress_state()

# Session State Initialization for Vocabulary Data (Auto-refresh if missing derivatives)
if "vocab_data" not in st.session_state or not st.session_state["vocab_data"] or "derivatives" not in st.session_state["vocab_data"][0]:
    st.session_state["vocab_data"] = load_default_vocab(
        os.path.join(os.path.dirname(__file__), "data", "default_vocab.json")
    )

if "active_unit" not in st.session_state:
    st.session_state["active_unit"] = 1

vocab_data = st.session_state["vocab_data"]
total_units = get_total_units(vocab_data)
total_words = len(vocab_data)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("## 🎓 700 單字學習與測驗 (v2 智能版)")
    st.caption("自動記憶個人進度 • 同單元打散測驗")

    # Multi-Child User Switcher (Timmy / Chloe)
    render_user_switcher_sidebar()

    st.markdown("---")

    # Main Navigation Mode
    nav_mode = st.radio(
        "導航功能",
        options=["📚 單元學習", "✍️ 隨堂測驗", "📊 學習儀表板", "📝 我的單字本", "📖 單字庫與上傳"],
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Unit Selector (Only when in Learning or Quiz mode)
    if nav_mode in ["📚 單元學習", "✍️ 隨堂測驗"]:
        st.markdown("### 📍 單元切換 (Unit Selector)")
        
        # Build unit display labels with completion badges
        completed_units = st.session_state.get("completed_units", set())
        quiz_scores = st.session_state.get("quiz_scores", {})
        
        unit_options = []
        for u in range(1, total_units + 1):
            score = quiz_scores.get(u)
            if score == 100:
                badge = "🏆 100%"
            elif score is not None and score >= 80:
                badge = f"✅ {score}%"
            elif score is not None:
                badge = f"✏️ {score}%"
            elif u in completed_units:
                badge = "📖 已學"
            else:
                badge = "⬜"
            unit_options.append(f"Unit {u:02d}  [{badge}]")

        current_idx = min(st.session_state["active_unit"] - 1, len(unit_options) - 1)
        selected_unit_str = st.selectbox(
            "選擇單元",
            options=unit_options,
            index=max(0, current_idx)
        )
        selected_unit = unit_options.index(selected_unit_str) + 1
        if selected_unit != st.session_state["active_unit"]:
            update_last_reading_position(selected_unit, 0)
            st.rerun()

        # Previous / Next Unit Buttons
        u_col1, u_col2 = st.columns(2)
        with u_col1:
            if st.button("⬅ 前一單元", use_container_width=True, disabled=(st.session_state["active_unit"] <= 1)):
                update_last_reading_position(st.session_state["active_unit"] - 1, 0)
                st.rerun()
        with u_col2:
            if st.button("後一單元 ➡", use_container_width=True, disabled=(st.session_state["active_unit"] >= total_units)):
                update_last_reading_position(st.session_state["active_unit"] + 1, 0)
                st.rerun()

    # Progress Mini Summary in Sidebar
    st.markdown("---")
    completed_cnt = len(st.session_state.get("completed_units", set()))
    st.markdown(f"**學習進度總覽：**")
    st.progress(completed_cnt / total_units if total_units else 0.0)
    st.caption(f"已完成: {completed_cnt} / {total_units} 單元 ({int(completed_cnt/total_units*100 if total_units else 0)}%)")

# ----------------- MAIN CONTENT AREA -----------------

active_unit = st.session_state.get("active_unit", 1)
unit_words = get_unit_words(vocab_data, active_unit)
current_user = st.session_state.get("current_user", "👦 Timmy")

if nav_mode == "📚 單元學習":
    card_idx_now = st.session_state.get(f"unit_{active_unit}_card_idx", 0) + 1
    st.markdown(f"## 📚 Unit {active_unit} 單元學習")
    st.caption(f"👤 當前學習者：**{current_user}** • 系統已為您自動載入上次閱讀位置：**Unit {active_unit:02d}** 第 **{card_idx_now}** 字")
    
    # Sub-tabs for Flashcard vs List View
    study_subtab = st.radio(
        "學習檢視模式",
        options=["🃏 單字卡模式 (Flashcard)", "📋 單字清單列表 (List View)"],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.markdown("<div style='margin-bottom: 14px;'></div>", unsafe_allow_html=True)

    if study_subtab == "🃏 單字卡模式 (Flashcard)":
        render_flashcard_view(unit_words, active_unit)
    else:
        render_word_list_view(unit_words, active_unit)

elif nav_mode == "✍️ 隨堂測驗":
    render_quiz_view(unit_words, vocab_data, active_unit)

elif nav_mode == "📊 學習儀表板":
    render_dashboard(total_units, total_words)

elif nav_mode == "📝 我的單字本":
    render_word_bank_page(current_user)

elif nav_mode == "📖 單字庫與上傳":
    st.markdown("## 📖 單字資料庫與資料管理")
    
    tab_dict, tab_upload, tab_template = st.tabs(["🔍 單字字典查詢", "📤 上傳自訂資料集", "📥 下載資料集範本"])

    with tab_dict:
        st.markdown("### 🔍 700 核心單字搜尋與檢視")
        s_col1, s_col2 = st.columns([3, 1])
        with s_col1:
            search_query = st.text_input("搜尋英文單字、中文釋義或英英解釋", placeholder="例如：abandon, 承認, power...")
        with s_col2:
            pos_filter = st.selectbox("詞性篩選", options=["All", "v.", "n.", "adj.", "adv."])

        search_results = search_vocabulary(vocab_data, search_query, pos_filter)
        st.caption(f"共找到 {len(search_results)} 筆單字")

        # Table display
        if search_results:
            rows_data = []
            for r in search_results:
                deriv_list = [f"{d['word']}({d['pos']})" for d in r.get("derivatives", [])]
                rows_data.append({
                    "編號": r.get("id", ""),
                    "單元": f"Unit {r.get('unit', '')}",
                    "單字": r.get("word", ""),
                    "音標": r.get("phonetic", ""),
                    "詞性": r.get("pos", ""),
                    "中文釋義": r.get("chinese_meaning", ""),
                    "英英解釋": r.get("english_definition", ""),
                    "🌱 衍生詞": ", ".join(deriv_list) if deriv_list else "-",
                    "🔗 類似詞": ", ".join(r.get("synonyms", [])) if r.get("synonyms") else "-",
                    "例句": r.get("example_sentence", "")
                })
            df_display = pd.DataFrame(rows_data)
            st.dataframe(df_display, use_container_width=True, height=480)
        else:
            st.info("查無符合條件的單字。")

    with tab_upload:
        st.markdown("### 📤 上傳自訂 CSV 或 JSON 單字庫")
        st.write("您可以上傳自己的單字檔案（支援 CSV 或 JSON 格式），系統將自動每 10 個單字劃分為一個單元。")

        uploaded_file = st.file_uploader("請選擇 CSV 或 JSON 檔案", type=["csv", "json"], key="dataset_uploader")
        
        if uploaded_file is not None:
            success, msg, new_data = parse_uploaded_file(uploaded_file)
            if success:
                st.success(msg)
                if st.button("確認套用此資料集", type="primary"):
                    st.session_state["vocab_data"] = new_data
                    st.session_state["active_unit"] = 1
                    st.session_state["completed_units"] = set()
                    st.session_state["quiz_scores"] = {}
                    st.rerun()
            else:
                st.error(msg)

    with tab_template:
        st.markdown("### 📥 下載標準單字格式範本")
        st.write("若您需要自行編寫單字集並匯入，請下載以下標準範本以確保欄位名稱正確：")

        template_csv_path = os.path.join(os.path.dirname(__file__), "data", "vocab_template.csv")
        if os.path.exists(template_csv_path):
            with open(template_csv_path, "r", encoding="utf-8") as f:
                csv_bytes = f.read().encode("utf-8-sig")
            st.download_button(
                label="📄 下載 CSV 資料集範本 (vocab_template.csv)",
                data=csv_bytes,
                file_name="vocab_template.csv",
                mime="text/csv"
            )

        # Download full default 700 dataset JSON
        default_json_path = os.path.join(os.path.dirname(__file__), "data", "default_vocab.json")
        if os.path.exists(default_json_path):
            with open(default_json_path, "r", encoding="utf-8") as f:
                json_bytes = f.read().encode("utf-8")
            st.download_button(
                label="📦 下載完整 700 單字 JSON 資料集 (default_vocab.json)",
                data=json_bytes,
                file_name="default_vocab.json",
                mime="application/json"
            )
