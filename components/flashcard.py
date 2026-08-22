"""
Interactive Flashcard and Word List components for Unit Learning Mode.
"""

import streamlit as st
import re
import html
from typing import List, Dict, Any
from components.audio_player import render_dual_speech_controls, render_speech_button
from components.progress_tracker import save_persistent_progress

def highlight_target_word(sentence: str, target_word: str) -> str:
    """Highlights the target word in the example sentence with custom HTML styling."""
    if not sentence or not target_word:
        return sentence or ""
    
    # Match root variations
    pattern = re.compile(rf"\b({re.escape(target_word)}[a-zA-Z]*)\b", re.IGNORECASE)
    highlighted = pattern.sub(r'<span class="target-word-highlight">\1</span>', html.escape(sentence))
    return highlighted

def render_flashcard_view(unit_words: List[Dict[str, Any]], unit_id: int):
    """Renders single-word flashcard mode with navigation and self-test toggles."""
    if not unit_words:
        st.warning("此單元無單字資料。")
        return

    # Session state key for current word index in this unit
    state_key = f"unit_{unit_id}_card_idx"
    if state_key not in st.session_state:
        st.session_state[state_key] = 0

    current_idx = st.session_state[state_key]
    # Bound check
    if current_idx >= len(unit_words):
        current_idx = 0
        st.session_state[state_key] = 0

    word_data = unit_words[current_idx]
    total_in_unit = len(unit_words)

    # Top Control Bar: Unit progress & self-test toggles
    top_col1, top_col2 = st.columns([3, 2])
    with top_col1:
        st.caption(f"📍 Unit {unit_id} • 單字進度 {current_idx + 1} / {total_in_unit}")
        st.progress((current_idx + 1) / total_in_unit)
    
    with top_col2:
        self_test = st.toggle("🧠 自我檢測模式 (遮蔽中文)", value=st.session_state.get(f"hide_meaning_{unit_id}", False), key=f"hide_meaning_{unit_id}")

    # Flashcard Card Container
    word = word_data.get("word", "")
    phonetic = word_data.get("phonetic", "")
    pos = word_data.get("pos", "")
    eng_def = word_data.get("english_definition", "")
    chi_meaning = word_data.get("chinese_meaning", "")
    example = word_data.get("example_sentence", "")

    highlighted_example = highlight_target_word(example, word)

    # Render Card with Glassmorphism / Shadow
    st.markdown(f"""
    <div class="flashcard-container">
        <div class="flashcard-header">
            <span class="pos-badge pos-{pos.lower().replace('.', '')}">{pos}</span>
            <span class="phonetic-text">{phonetic}</span>
            <span class="word-id-tag">#{word_data.get('id', current_idx+1)}</span>
        </div>
        <div class="flashcard-word-title">{word}</div>
    </div>
    """, unsafe_allow_html=True)

    # Audio Controls
    render_dual_speech_controls(word=word, sentence=example, rate=0.95)

    # Meanings and definitions
    with st.container():
        st.markdown('<div class="definition-box">', unsafe_allow_html=True)
        
        # English Definition
        st.markdown(f"**📖 English Definition:**")
        st.markdown(f"<div class='english-def-text'>{eng_def or 'No definition provided.'}</div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px dashed #e5e7eb;' />", unsafe_allow_html=True)

        # Chinese Meaning
        st.markdown(f"**🇹🇼 中文釋義:**")
        if self_test:
            with st.expander("👁️ 點擊查看中文解釋", expanded=False):
                st.markdown(f"<div class='chinese-meaning-text'>{chi_meaning}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chinese-meaning-text'>{chi_meaning}</div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px dashed #e5e7eb;' />", unsafe_allow_html=True)

        # Example Sentence
        st.markdown(f"**💡 例句範例 (Example):**")
        st.markdown(f"<div class='example-sentence-text'>“{highlighted_example}”</div>", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Navigation Buttons
    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
    with nav_col1:
        if st.button("◀ 上一個", use_container_width=True, disabled=(current_idx == 0)):
            st.session_state[state_key] = max(0, current_idx - 1)
            st.rerun()

    with nav_col2:
        # Quick dropdown selector
        options = [f"{i+1}. {w.get('word', '')}" for i, w in enumerate(unit_words)]
        selected_option = st.selectbox(
            "快速跳轉單字",
            options=options,
            index=current_idx,
            label_visibility="collapsed",
            key=f"select_word_unit_{unit_id}"
        )
        new_idx = options.index(selected_option)
        if new_idx != current_idx:
            st.session_state[state_key] = new_idx
            st.rerun()

    with nav_col3:
        if current_idx < total_in_unit - 1:
            if st.button("下一個 ▶", use_container_width=True, type="primary"):
                st.session_state[state_key] = current_idx + 1
                st.rerun()
        else:
            if st.button("🎉 完成單元", use_container_width=True, type="primary"):
                # Mark unit as completed in progress state
                if "completed_units" not in st.session_state:
                    st.session_state["completed_units"] = set()
                st.session_state["completed_units"].add(unit_id)
                save_persistent_progress()
                st.balloons()
                st.success(f"太棒了！您已完成 Unit {unit_id} 的全部單字學習！可以前往「隨堂測驗」進行測驗挑戰！")

def render_word_list_view(unit_words: List[Dict[str, Any]], unit_id: int):
    """Renders complete 10-word list table/card overview for the current unit."""
    st.markdown(f"### 📋 Unit {unit_id} 單字總覽清單 (共 {len(unit_words)} 字)")
    
    for idx, item in enumerate(unit_words, 1):
        word = item.get("word", "")
        phonetic = item.get("phonetic", "")
        pos = item.get("pos", "")
        chi = item.get("chinese_meaning", "")
        eng = item.get("english_definition", "")
        ex = item.get("example_sentence", "")

        with st.container():
            st.markdown(f"""
            <div class="word-list-row">
                <div style="display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;">
                    <span style="font-weight: 700; font-size: 1.1rem; color: #1e293b;">{idx}. {word}</span>
                    <span class="pos-badge pos-{pos.lower().replace('.', '')}">{pos}</span>
                    <span style="color: #64748b; font-family: monospace;">{phonetic}</span>
                    <span style="font-weight: 600; color: #2563eb; margin-left: auto;">{chi}</span>
                </div>
                <div style="margin-top: 6px; font-size: 0.92rem; color: #475569;">
                    <strong>釋義:</strong> {eng}
                </div>
                <div style="margin-top: 4px; font-size: 0.88rem; color: #64748b; font-style: italic;">
                    <strong>例句:</strong> {ex}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Inline pronunciation button for each word in the list
            render_speech_button(text=word, label=f"🔊 朗讀 {word}", rate=0.95, key=f"list_tts_{unit_id}_{idx}", height=38)
            st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
