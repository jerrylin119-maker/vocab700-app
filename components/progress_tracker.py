"""
Multi-Child Learning Progress Tracker and Visual Dashboard module.
Supports independent profiles for Timmy, Chloe, and custom learners.
Auto-persists progress to user_progress.json, with side-by-side comparison and error diagnosis.
"""

import os
import json
import datetime
import streamlit as st
from typing import List, Dict, Any

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "user_progress.json")
DEFAULT_PROFILES = ["👦 Timmy", "👧 Chloe"]

def load_persistent_progress() -> Dict[str, Any]:
    """Loads saved progress from user_progress.json file."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "users" not in data or not data["users"]:
                    data["users"] = {
                        "👦 Timmy": {"completed_units": [], "quiz_scores": {}, "quiz_history": []},
                        "👧 Chloe": {"completed_units": [], "quiz_scores": {}, "quiz_history": []}
                    }
                return data
        except Exception as e:
            print(f"Error loading progress file: {e}")
    return {
        "current_user": "👦 Timmy",
        "users": {
            "👦 Timmy": {"completed_units": [], "quiz_scores": {}, "quiz_history": []},
            "👧 Chloe": {"completed_units": [], "quiz_scores": {}, "quiz_history": []}
        }
    }

def save_persistent_progress():
    """Saves current session progress to user_progress.json file."""
    try:
        data = load_persistent_progress()
        user = st.session_state.get("current_user", "👦 Timmy")
        if "users" not in data:
            data["users"] = {}
        
        data["current_user"] = user
        data["users"][user] = {
            "completed_units": list(st.session_state.get("completed_units", set())),
            "quiz_scores": {str(k): v for k, v in st.session_state.get("quiz_scores", {}).items()},
            "quiz_history": st.session_state.get("quiz_history", [])
        }
        
        os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving progress file: {e}")

def switch_user(new_user: str):
    """Switches the active user and loads their respective progress."""
    # First save current user's state
    if "current_user" in st.session_state:
        save_persistent_progress()
        
    data = load_persistent_progress()
    st.session_state["current_user"] = new_user
    user_data = data.get("users", {}).get(new_user, {"completed_units": [], "quiz_scores": {}, "quiz_history": []})
    
    st.session_state["completed_units"] = set(user_data.get("completed_units", []))
    st.session_state["quiz_scores"] = {int(k): v for k, v in user_data.get("quiz_scores", {}).items()}
    st.session_state["quiz_history"] = user_data.get("quiz_history", [])

def init_progress_state():
    """Initializes persistent progress states from persistent file or defaults."""
    if "progress_initialized" not in st.session_state:
        saved = load_persistent_progress()
        current_user = saved.get("current_user", "👦 Timmy")
        st.session_state["current_user"] = current_user
        
        user_data = saved.get("users", {}).get(current_user, {"completed_units": [], "quiz_scores": {}, "quiz_history": []})
        st.session_state["completed_units"] = set(user_data.get("completed_units", []))
        st.session_state["quiz_scores"] = {int(k): v for k, v in user_data.get("quiz_scores", {}).items()}
        st.session_state["quiz_history"] = user_data.get("quiz_history", [])
        st.session_state["progress_initialized"] = True

def render_user_switcher_sidebar():
    """Renders student profile switcher in sidebar."""
    init_progress_state()
    data = load_persistent_progress()
    existing_users = list(data.get("users", {}).keys())
    if "👦 Timmy" not in existing_users:
        existing_users.insert(0, "👦 Timmy")
    if "👧 Chloe" not in existing_users:
        existing_users.insert(1, "👧 Chloe")
    
    current_user = st.session_state.get("current_user", "👦 Timmy")
    if current_user not in existing_users:
        existing_users.append(current_user)

    st.sidebar.markdown("### 👤 學習者身分 (Active Learner)")
    selected_user = st.sidebar.selectbox(
        "選擇學習者",
        options=existing_users,
        index=existing_users.index(current_user) if current_user in existing_users else 0,
        label_visibility="collapsed",
        key="sidebar_user_selector"
    )

    if selected_user != current_user:
        switch_user(selected_user)
        st.rerun()

    # Expandable to add new student profile
    with st.sidebar.expander("➕ 新增其他學員", expanded=False):
        new_name = st.text_input("輸入新學員姓名", key="new_student_name_input", placeholder="例如：Leo")
        if st.button("確認新增", use_container_width=True):
            if new_name.strip():
                formatted_name = f"🌟 {new_name.strip()}"
                data["users"][formatted_name] = {"completed_units": [], "quiz_scores": {}, "quiz_history": []}
                with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                switch_user(formatted_name)
                st.success(f"已新增並切換至 {formatted_name}！")
                st.rerun()

def record_quiz_attempt(unit_id: int, score_pct: int, correct_cnt: int, total_cnt: int, wrong_words: List[str]):
    """Records a single quiz attempt with timestamp into history and persists to file."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = {
        "timestamp": now_str,
        "unit": unit_id,
        "score": score_pct,
        "correct": correct_cnt,
        "total": total_cnt,
        "wrong_words": wrong_words
    }
    if "quiz_history" not in st.session_state:
        st.session_state["quiz_history"] = []
    
    st.session_state["quiz_history"].insert(0, entry) # latest first
    st.session_state["quiz_history"] = st.session_state["quiz_history"][:50]
    
    # Save high score
    if "quiz_scores" not in st.session_state:
        st.session_state["quiz_scores"] = {}
    prev = st.session_state["quiz_scores"].get(unit_id, 0)
    if score_pct > prev:
        st.session_state["quiz_scores"][unit_id] = score_pct

    # Mark completed
    if "completed_units" not in st.session_state:
        st.session_state["completed_units"] = set()
    st.session_state["completed_units"].add(unit_id)

    save_persistent_progress()

def render_dashboard(total_units: int, total_words: int):
    """Renders the comprehensive learning statistics dashboard, dual-child PK comparison, and parent view."""
    init_progress_state()
    data = load_persistent_progress()
    all_users = data.get("users", {})

    current_user = st.session_state.get("current_user", "👦 Timmy")
    completed_units = st.session_state["completed_units"]
    quiz_scores = st.session_state["quiz_scores"]
    quiz_history = st.session_state.get("quiz_history", [])

    completed_count = len(completed_units)
    quizzes_taken = len(quiz_scores)
    avg_score = int(sum(quiz_scores.values()) / len(quiz_scores)) if quiz_scores else 0
    mastered_count = sum(1 for s in quiz_scores.values() if s == 100)
    passed_count = sum(1 for s in quiz_scores.values() if s >= 80)

    # Top Header & User Identity
    st.markdown(f"## 📊 【{current_user}】的學習進度與數據儀表板")
    st.caption("支援 Timmy 與 Chloe 獨立分開記錄 • 70 單元掌握度色塊圖 • 雙寶學習榮譽榜")

    # Top Metric Cards for Active User
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("📚 已學習單元", f"{completed_count} / {total_units}", f"{int(completed_count/total_units*100 if total_units else 0)}% 完成率")
    with m2:
        st.metric("🎯 已測驗單元", f"{quizzes_taken} / {total_units}", f"通過 {passed_count} 單元 (≥80分)")
    with m3:
        st.metric("🏆 滿分單元 (100分)", f"{mastered_count} 單元", f"{int(mastered_count/total_units*100 if total_units else 0)}% 完美掌握")
    with m4:
        st.metric("📈 測驗平均成績", f"{avg_score} 分", "歷史綜合平均")

    st.markdown("---")

    # Dashboard Tabs
    tab_matrix, tab_comparison, tab_history = st.tabs([
        f"🗺️ 【{current_user}】70 單元掌握度矩陣",
        "🏆 雙寶學習榮譽榜 (Timmy vs Chloe 對比)",
        "📝 家長聯絡簿：測驗歷程與錯題診斷"
    ])

    # 1. Active User Matrix
    with tab_matrix:
        st.markdown(f"### 🗺️ 【{current_user}】全單元掌握度分佈圖 (70 Units Matrix)")
        st.markdown("""
        **各單元狀態標記：** 
        <span class="legend-badge bg-gold">🏆 100% 滿分</span> &nbsp;
        <span class="legend-badge bg-green">✅ 80-90% 通過</span> &nbsp;
        <span class="legend-badge bg-yellow">✏️ 60-70% 待加強</span> &nbsp;
        <span class="legend-badge bg-blue">📖 已學習 (未測驗)</span> &nbsp;
        <span class="legend-badge bg-gray">⬜ 未學習</span>
        """, unsafe_allow_html=True)
        st.write("")

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
                    badge = f"🏆 100"
                elif score is not None and score >= 80:
                    bg_color = "#bbf7d0" # Green
                    border_color = "#22c55e"
                    text_color = "#15803d"
                    badge = f"✅ {score}"
                elif score is not None and score >= 60:
                    bg_color = "#fed7aa" # Orange/Yellow
                    border_color = "#f97316"
                    text_color = "#9a3412"
                    badge = f"✏️ {score}"
                elif score is not None and score < 60:
                    bg_color = "#fecaca" # Red
                    border_color = "#ef4444"
                    text_color = "#991b1b"
                    badge = f"⚠️ {score}"
                elif is_learned:
                    bg_color = "#bfdbfe" # Blue
                    border_color = "#3b82f6"
                    text_color = "#1e40af"
                    badge = "📖 已學"
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
                        padding: 8px 2px;
                        text-align: center;
                        margin-bottom: 8px;
                        font-family: monospace;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                    ">
                        <div style="font-weight: 700; font-size: 0.85rem;">U{u_id:02d}</div>
                        <div style="font-size: 0.72rem; font-weight: 600;">{badge}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # 2. Dual-Child Comparison
    with tab_comparison:
        st.markdown("### 🏆 雙寶學習進度對比榜")
        st.caption("方便家長同時檢視 Timmy 與 Chloe 的學習成效，互相鼓勵！")

        user_list = list(all_users.keys())
        comp_cols = st.columns(len(user_list) if user_list else 2)

        for idx, u_name in enumerate(user_list):
            u_info = all_users[u_name]
            u_comp_units = set(u_info.get("completed_units", []))
            u_scores = {int(k): v for k, v in u_info.get("quiz_scores", {}).items()}
            u_avg = int(sum(u_scores.values()) / len(u_scores)) if u_scores else 0
            u_mastered = sum(1 for s in u_scores.values() if s == 100)

            with comp_cols[idx]:
                st.markdown(f"""
                <div style="
                    background: #ffffff;
                    border: 2px solid {'#3b82f6' if u_name == current_user else '#e2e8f0'};
                    border-radius: 14px;
                    padding: 20px;
                    text-align: center;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                    margin-bottom: 16px;
                ">
                    <h3 style="margin: 0; color: #1e293b;">{u_name}</h3>
                    <div style="font-size: 0.85rem; color: {'#2563eb' if u_name == current_user else '#64748b'}; font-weight: 600; margin-bottom: 12px;">
                        {'（目前使用中）' if u_name == current_user else ' '}
                    </div>
                    <div style="display: flex; justify-content: space-around; margin-top: 10px;">
                        <div>
                            <div style="font-size: 0.8rem; color: #64748b;">已學單元</div>
                            <div style="font-size: 1.4rem; font-weight: 700; color: #2563eb;">{len(u_comp_units)}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.8rem; color: #64748b;">測驗均分</div>
                            <div style="font-size: 1.4rem; font-weight: 700; color: #16a34a;">{u_avg} 分</div>
                        </div>
                        <div>
                            <div style="font-size: 0.8rem; color: #64748b;">滿分次數</div>
                            <div style="font-size: 1.4rem; font-weight: 700; color: #d97706;">{u_mastered} 次</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if u_name != current_user:
                    if st.button(f"切換為 {u_name} 視角", key=f"btn_switch_{idx}", use_container_width=True):
                        switch_user(u_name)
                        st.rerun()

    # 3. Parent Diagnostics History
    with tab_history:
        st.markdown("### 📝 家長聯絡簿：測驗時間軸與錯題診斷")
        filter_user = st.selectbox("選擇要檢視的孩子", options=list(all_users.keys()), index=list(all_users.keys()).index(current_user) if current_user in all_users else 0)
        
        target_history = all_users.get(filter_user, {}).get("quiz_history", [])
        if not target_history:
            st.info(f"【{filter_user}】目前尚無測驗紀錄。當孩子完成任何單元的隨堂測驗後，這裡會即時顯示測驗時間、成績與容易拼錯的單字！")
        else:
            st.write(f"以下記錄了 **{filter_user}** 最近的測驗成果：")
            
            for h in target_history:
                u_num = h.get("unit", 1)
                score = h.get("score", 0)
                t_str = h.get("timestamp", "")
                c_cnt = h.get("correct", 0)
                tot = h.get("total", 10)
                wrongs = h.get("wrong_words", [])

                card_border = "#22c55e" if score >= 80 else ("#f59e0b" if score >= 60 else "#ef4444")
                score_color = "#15803d" if score >= 80 else ("#b45309" if score >= 60 else "#b91c1c")

                st.markdown(f"""
                <div style="
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-left: 5px solid {card_border};
                    border-radius: 10px;
                    padding: 14px 18px;
                    margin-bottom: 10px;
                    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <span style="font-weight: 700; font-size: 1.1rem; color: #1e293b;">
                            📖 Unit {u_num:02d} 隨堂測驗
                        </span>
                        <span style="font-size: 0.85rem; color: #64748b;">⏱️ 測驗時間：{t_str}</span>
                    </div>
                    <div style="margin-top: 6px; font-size: 1rem;">
                        得分：<strong style="color: {score_color}; font-size: 1.25rem;">{score} 分</strong> 
                        <span style="color: #64748b; font-size: 0.9rem;">(答對 {c_cnt} / {tot} 題)</span>
                    </div>
                    <div style="margin-top: 6px; font-size: 0.92rem; color: #475569;">
                        {'🎉 本次測驗全對，單字掌握非常熟練！' if not wrongs else f'⚠️ 需多加複習的單字：<strong style="color: #dc2626;">{", ".join(wrongs)}</strong>'}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # Data Backup & Restore Management
    st.markdown("### 💾 全部小孩進度備份與還原 (Data Export / Import)")
    col_exp, col_imp, col_rst = st.columns(3)

    with col_exp:
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 匯出全家學習紀錄 (JSON)",
            data=json_str,
            file_name="all_kids_vocab700_progress.json",
            mime="application/json",
            use_container_width=True
        )
        st.caption("包含 Timmy 與 Chloe 的所有學習與測驗紀錄。")

    with col_imp:
        upload_backup = st.file_uploader("匯入學習進度 (JSON)", type=["json"], key="backup_uploader")
        if upload_backup is not None:
            try:
                loaded = json.load(upload_backup)
                with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                    json.dump(loaded, f, ensure_ascii=False, indent=2)
                switch_user(loaded.get("current_user", "👦 Timmy"))
                st.success("成功還原全體小孩的學習進度！")
                st.rerun()
            except Exception as e:
                st.error(f"還原失敗: {e}")

    with col_rst:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button(f"🗑️ 重設【{current_user}】的進度", use_container_width=True):
            st.session_state["completed_units"] = set()
            st.session_state["quiz_scores"] = {}
            st.session_state["quiz_history"] = []
            save_persistent_progress()
            st.warning(f"{current_user} 的學習紀錄已重設！")
            st.rerun()
