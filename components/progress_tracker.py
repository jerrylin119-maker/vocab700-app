"""
Learning Progress Tracker and Visual Dashboard module.
Tracks unit completion status, quiz scores, high score matrix, and export/import.
"""

import json
import streamlit as st
from typing import List, Dict, Any

def init_progress_state():
    """Initializes persistent progress states in st.session_state."""
    if "completed_units" not in st.session_state:
        st.session_state["completed_units"] = set()
    if "quiz_scores" not in st.session_state:
        st.session_state["quiz_scores"] = {}
    if "quiz_history" not in st.session_state:
        st.session_state["quiz_history"] = []

def render_dashboard(total_units: int, total_words: int):
    """Renders the comprehensive learning statistics dashboard and unit matrix."""
    init_progress_state()

    completed_units = st.session_state["completed_units"]
    quiz_scores = st.session_state["quiz_scores"]

    completed_count = len(completed_units)
    quizzes_taken = len(quiz_scores)
    avg_score = int(sum(quiz_scores.values()) / len(quiz_scores)) if quiz_scores else 0
    mastered_count = sum(1 for s in quiz_scores.values() if s == 100)
    passed_count = sum(1 for s in quiz_scores.values() if s >= 80)

    st.markdown("## 📊 學習進度與數據儀表板")
    st.caption("即時追蹤您的 700 單字學習歷程、測驗成績分佈與各單元掌握度。")

    # Top Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("📚 已學習單元", f"{completed_count} / {total_units}", f"{int(completed_count/total_units*100 if total_units else 0)}% 完成率")
    with m2:
        st.metric("🎯 已測驗單元", f"{quizzes_taken} / {total_units}", f"通過 {passed_count} 單元")
    with m3:
        st.metric("🏆 滿分單元 (100%)", f"{mastered_count} 單元", f"{int(mastered_count/total_units*100 if total_units else 0)}% 完美掌握")
    with m4:
        st.metric("📈 測驗平均成績", f"{avg_score}%", "歷史平均得分")

    st.markdown("---")

    # Unit Mastery Matrix (70 Units Grid)
    st.markdown("### 🗺️ 全單元掌握度矩陣 (70 Units Matrix)")
    st.markdown("""
    **圖例說明：** 
    <span class="legend-badge bg-gold">🏆 100% 滿分</span> &nbsp;
    <span class="legend-badge bg-green">✅ 80-90% 通過</span> &nbsp;
    <span class="legend-badge bg-yellow">✏️ 60-70% 待加強</span> &nbsp;
    <span class="legend-badge bg-blue">📖 已學習 (未測驗)</span> &nbsp;
    <span class="legend-badge bg-gray">⬜ 未學習</span>
    """, unsafe_allow_html=True)

    # Render matrix in rows of 10
    cols_per_row = 10
    for row_start in range(1, total_units + 1, cols_per_row):
        row_units = range(row_start, min(row_start + cols_per_row, total_units + 1))
        cols = st.columns(cols_per_row)
        for idx, u_id in enumerate(row_units):
            score = quiz_scores.get(u_id, None)
            is_learned = u_id in completed_units

            if score == 100:
                bg_color = "#fef08a" # Gold
                border_color = "#eab308"
                text_color = "#854d0e"
                badge = f"🏆 {score}%"
            elif score is not None and score >= 80:
                bg_color = "#bbf7d0" # Green
                border_color = "#22c55e"
                text_color = "#15803d"
                badge = f"✅ {score}%"
            elif score is not None and score >= 60:
                bg_color = "#fed7aa" # Orange/Yellow
                border_color = "#f97316"
                text_color = "#9a3412"
                badge = f"✏️ {score}%"
            elif score is not None and score < 60:
                bg_color = "#fecaca" # Red
                border_color = "#ef4444"
                text_color = "#991b1b"
                badge = f"⚠️ {score}%"
            elif is_learned:
                bg_color = "#bfdbfe" # Blue
                border_color = "#3b82f6"
                text_color = "#1e40af"
                badge = "📖 已學習"
            else:
                bg_color = "#f3f4f6" # Gray
                border_color = "#e5e7eb"
                text_color = "#6b7280"
                badge = "未開始"

            with cols[idx]:
                st.markdown(f"""
                <div style="
                    background: {bg_color};
                    border: 1px solid {border_color};
                    color: {text_color};
                    border-radius: 8px;
                    padding: 8px 4px;
                    text-align: center;
                    margin-bottom: 8px;
                    font-family: monospace;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                ">
                    <div style="font-weight: 700; font-size: 0.85rem;">U{u_id:02d}</div>
                    <div style="font-size: 0.72rem; font-weight: 600;">{badge}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # Data Backup & Restore Management
    st.markdown("### 💾 進度備份與還原 (Data Export / Import)")
    col_exp, col_imp, col_rst = st.columns(3)

    with col_exp:
        progress_data = {
            "completed_units": list(completed_units),
            "quiz_scores": quiz_scores
        }
        json_str = json.dumps(progress_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 匯出學習紀錄 (JSON)",
            data=json_str,
            file_name="vocab700_progress_backup.json",
            mime="application/json",
            use_container_width=True
        )
        st.caption("將目前的學習與測驗進度儲存為 JSON 備份檔案。")

    with col_imp:
        upload_backup = st.file_uploader("匯入學習進度 (JSON)", type=["json"], key="backup_uploader")
        if upload_backup is not None:
            try:
                loaded = json.load(upload_backup)
                st.session_state["completed_units"] = set(loaded.get("completed_units", []))
                st.session_state["quiz_scores"] = {int(k): v for k, v in loaded.get("quiz_scores", {}).items()}
                st.success("成功還原學習進度！")
                st.rerun()
            except Exception as e:
                st.error(f"還原失敗: {e}")

    with col_rst:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🗑️ 重設全部進度", use_container_width=True):
            st.session_state["completed_units"] = set()
            st.session_state["quiz_scores"] = {}
            st.session_state["quiz_history"] = []
            st.warning("所有學習紀錄已重設！")
            st.rerun()
