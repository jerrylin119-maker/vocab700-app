"""
Multi-Child Learning Progress Tracker and Visual Dashboard module.
Supports independent profiles for Timmy, Chloe, and custom learners.

PERSISTENCE STRATEGY:
  Primary:  GitHub API → data-storage branch → data/user_progress.json
            (survives Streamlit Cloud container restarts)
  Fallback: Local filesystem (works in local dev, lost on server restart)

GitHub token is read from st.secrets["GITHUB_TOKEN"].
"""

import os
import json
import datetime
import urllib.request
import urllib.error
import base64
import streamlit as st
from typing import List, Dict, Any

# ── Config ────────────────────────────────────────────────────────────────────
PROGRESS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "user_progress.json")
DEFAULT_PROFILES = ["👦 Timmy", "👧 Chloe"]
_GH_OWNER  = "jerrylin119-maker"
_GH_REPO   = "vocab700-app"
_GH_BRANCH = "data-storage"
_GH_PATH   = "data/user_progress.json"


def _gh_token() -> str:
    try:
        return st.secrets.get("GITHUB_TOKEN", "")
    except Exception:
        return ""


def _gh_headers(token: str) -> dict:
    return {
        "Authorization": "token " + token,
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "vocab700-app"
    }


def _load_from_github() -> Dict | None:
    """Loads user_progress.json from the data-storage branch via GitHub API."""
    token = _gh_token()
    if not token:
        return None
    try:
        url = (
            "https://api.github.com/repos/" + _GH_OWNER + "/" + _GH_REPO
            + "/contents/" + _GH_PATH + "?ref=" + _GH_BRANCH
        )
        req = urllib.request.Request(url, headers=_gh_headers(token))
        with urllib.request.urlopen(req, timeout=8) as r:
            meta = json.loads(r.read())
        content = base64.b64decode(meta["content"]).decode("utf-8")
        return json.loads(content)
    except Exception:
        return None


def _save_to_github(data: Dict):
    """Saves user_progress.json to the data-storage branch via GitHub API."""
    token = _gh_token()
    if not token:
        return
    try:
        # Get current SHA first
        url = (
            "https://api.github.com/repos/" + _GH_OWNER + "/" + _GH_REPO
            + "/contents/" + _GH_PATH + "?ref=" + _GH_BRANCH
        )
        req = urllib.request.Request(url, headers=_gh_headers(token))
        sha = ""
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                meta = json.loads(r.read())
                sha = meta.get("sha", "")
        except Exception:
            pass

        content_str = json.dumps(data, ensure_ascii=False, indent=2)
        encoded = base64.b64encode(content_str.encode("utf-8")).decode()

        payload_dict = {
            "message": "Auto-save progress",
            "content": encoded,
            "branch": _GH_BRANCH
        }
        if sha:
            payload_dict["sha"] = sha

        put_url = (
            "https://api.github.com/repos/" + _GH_OWNER + "/" + _GH_REPO
            + "/contents/" + _GH_PATH
        )
        put_req = urllib.request.Request(
            put_url,
            data=json.dumps(payload_dict).encode(),
            headers=_gh_headers(token),
            method="PUT"
        )
        urllib.request.urlopen(put_req, timeout=10)
    except Exception:
        pass  # silently fail — local save still happened


def get_default_user_data() -> Dict[str, Any]:
    return {
        "completed_units": [],
        "quiz_scores": {},
        "quiz_history": [],
        "last_unit": 1,
        "last_card_index": 0,
        "last_study_time": "",
        "my_words": []
    }


def load_persistent_progress() -> Dict[str, Any]:
    """Loads saved progress. GitHub API is primary; local file is fallback."""
    # Try GitHub first (survives server restarts)
    gh_data = _load_from_github()
    if gh_data and "users" in gh_data:
        data = gh_data
    elif os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    else:
        data = {}

    # Ensure structure
    if "users" not in data or not data["users"]:
        data["users"] = {
            "👦 Timmy": get_default_user_data(),
            "👧 Chloe": get_default_user_data()
        }
    if "current_user" not in data:
        data["current_user"] = "👦 Timmy"

    # Back-fill missing fields for each user
    for u_val in data["users"].values():
        for field, default in [
            ("last_unit", 1), ("last_card_index", 0),
            ("last_study_time", ""), ("my_words", [])
        ]:
            if field not in u_val:
                u_val[field] = default

    return data


def save_persistent_progress():
    """Saves current session progress both locally and to GitHub."""
    try:
        data = load_persistent_progress()
        user = st.session_state.get("current_user", "👦 Timmy")
        active_u = st.session_state.get("active_unit", 1)
        active_c = st.session_state.get(f"unit_{active_u}_card_idx", 0)

        if "users" not in data:
            data["users"] = {}

        data["current_user"] = user
        data["users"][user] = {
            "completed_units": list(st.session_state.get("completed_units", set())),
            "quiz_scores": {str(k): v for k, v in st.session_state.get("quiz_scores", {}).items()},
            "quiz_history": st.session_state.get("quiz_history", []),
            "last_unit": active_u,
            "last_card_index": active_c,
            "last_study_time": st.session_state.get(
                "last_study_time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            ),
            "my_words": data["users"].get(user, {}).get("my_words", [])
        }

        # Save locally (fast, used within same container lifetime)
        os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Save to GitHub (persistent across server restarts)
        _save_to_github(data)

    except Exception as e:
        st.warning(f"⚠️ 進度儲存時發生錯誤: {e}")


def update_last_reading_position(unit_id: int, card_idx: int = 0):
    """Updates the active reading position and persists immediately."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    st.session_state["active_unit"] = unit_id
    st.session_state[f"unit_{unit_id}_card_idx"] = card_idx
    st.session_state["last_study_time"] = now_str
    save_persistent_progress()


def switch_user(new_user: str):
    """Switches the active user and restores their progress."""
    if "current_user" in st.session_state:
        save_persistent_progress()

    data = load_persistent_progress()
    st.session_state["current_user"] = new_user
    user_data = data.get("users", {}).get(new_user, get_default_user_data())

    st.session_state["completed_units"] = set(user_data.get("completed_units", []))
    st.session_state["quiz_scores"] = {int(k): v for k, v in user_data.get("quiz_scores", {}).items()}
    st.session_state["quiz_history"] = user_data.get("quiz_history", [])

    last_u = max(1, int(user_data.get("last_unit", 1)))
    last_c = max(0, int(user_data.get("last_card_index", 0)))
    st.session_state["active_unit"] = last_u
    st.session_state[f"unit_{last_u}_card_idx"] = last_c
    st.session_state["last_study_time"] = user_data.get("last_study_time", "")

    for k in [key for key in st.session_state if
              key.startswith("quiz_questions_unit_") or
              key.startswith("quiz_submitted_unit_") or
              key.startswith("quiz_answers_unit_")]:
        del st.session_state[k]


def init_progress_state():
    """Initializes persistent progress states (called once per session)."""
    if "progress_initialized" not in st.session_state:
        saved = load_persistent_progress()
        current_user = saved.get("current_user", "👦 Timmy")
        st.session_state["current_user"] = current_user

        user_data = saved.get("users", {}).get(current_user, get_default_user_data())
        st.session_state["completed_units"] = set(user_data.get("completed_units", []))
        st.session_state["quiz_scores"] = {
            int(k): v for k, v in user_data.get("quiz_scores", {}).items()
        }
        st.session_state["quiz_history"] = user_data.get("quiz_history", [])

        last_u = max(1, int(user_data.get("last_unit", 1)))
        last_c = max(0, int(user_data.get("last_card_index", 0)))
        st.session_state["active_unit"] = last_u
        st.session_state[f"unit_{last_u}_card_idx"] = last_c
        st.session_state["last_study_time"] = user_data.get("last_study_time", "")

        st.session_state["progress_initialized"] = True


def render_user_switcher_sidebar():
    """Renders student profile switcher in sidebar."""
    init_progress_state()
    data = load_persistent_progress()
    existing_users = list(data.get("users", {}).keys())
    for default in ["👦 Timmy", "👧 Chloe"]:
        if default not in existing_users:
            existing_users.insert(0 if default == "👦 Timmy" else 1, default)

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

    user_data = data.get("users", {}).get(current_user, {})
    last_u = user_data.get("last_unit", 1)
    last_c = user_data.get("last_card_index", 0) + 1
    st.sidebar.caption(f"📌 目前進度：**Unit {last_u:02d}** 第 **{last_c}** 字")

    with st.sidebar.expander("➕ 新增其他學員", expanded=False):
        new_name = st.text_input("輸入新學員姓名", key="new_student_name_input", placeholder="例如：Leo")
        if st.button("確認新增", use_container_width=True):
            if new_name.strip():
                formatted_name = f"🌟 {new_name.strip()}"
                data["users"][formatted_name] = get_default_user_data()
                _save_to_github(data)
                os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
                with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                switch_user(formatted_name)
                st.success(f"已新增並切換至 {formatted_name}！")
                st.rerun()


def record_quiz_attempt(unit_id: int, score_pct: int, correct_cnt: int, total_cnt: int, wrong_words: List[str]):
    """Records a single quiz attempt and persists to GitHub."""
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
    st.session_state["quiz_history"].insert(0, entry)
    st.session_state["quiz_history"] = st.session_state["quiz_history"][:50]

    if "quiz_scores" not in st.session_state:
        st.session_state["quiz_scores"] = {}
    prev = st.session_state["quiz_scores"].get(unit_id, 0)
    if score_pct > prev:
        st.session_state["quiz_scores"][unit_id] = score_pct

    if "completed_units" not in st.session_state:
        st.session_state["completed_units"] = set()
    st.session_state["completed_units"].add(unit_id)

    save_persistent_progress()


def render_dashboard(total_units: int, total_words: int):
    """Renders the comprehensive learning statistics dashboard."""
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

    st.markdown(f"## 📊 【{current_user}】的學習進度與數據儀表板")
    st.caption("支援 Timmy 與 Chloe 獨立分開記錄 • 記住每個人上次閱讀進度 • 雙寶學習榮譽榜")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("📚 已學習單元", f"{completed_count} / {total_units}",
                  f"{int(completed_count/total_units*100 if total_units else 0)}% 完成率")
    with m2:
        st.metric("🎯 已測驗單元", f"{quizzes_taken} / {total_units}",
                  f"通過 {passed_count} 單元 (≥80分)")
    with m3:
        st.metric("🏆 滿分單元 (100分)", f"{mastered_count} 單元",
                  f"{int(mastered_count/total_units*100 if total_units else 0)}% 完美掌握")
    with m4:
        st.metric("📈 測驗平均成績", f"{avg_score} 分", "歷史綜合平均")

    st.markdown("---")

    tab_matrix, tab_comparison, tab_history = st.tabs([
        f"🗺️ 【{current_user}】70 單元掌握度矩陣",
        "🏆 雙寶學習榮譽榜 (Timmy vs Chloe 對比)",
        "📝 家長聯絡簿：測驗歷程與錯題診斷"
    ])

    with tab_matrix:
        st.markdown(f"### 🗺️ 【{current_user}】全單元掌握度分佈圖")
        st.markdown("""
        **各單元狀態標記：**
        <span class="legend-badge bg-gold">🏆 100% 滿分</span> &nbsp;
        <span class="legend-badge bg-green">✅ 80-90% 通過</span> &nbsp;
        <span class="legend-badge bg-yellow">✏️ 60-70% 待加強</span> &nbsp;
        <span class="legend-badge bg-blue">📖 已學習 (未測驗)</span> &nbsp;
        <span class="legend-badge bg-gray">⬜ 未學習</span>
        """, unsafe_allow_html=True)
        st.write("")

        cols_per_row = 10
        for row_start in range(1, total_units + 1, cols_per_row):
            row_units = range(row_start, min(row_start + cols_per_row, total_units + 1))
            cols = st.columns(cols_per_row)
            for idx, u_id in enumerate(row_units):
                score = quiz_scores.get(u_id, None)
                is_learned = u_id in completed_units
                if score == 100:
                    bg, border, txt, badge = "#fef08a", "#eab308", "#854d0e", "🏆 100"
                elif score is not None and score >= 80:
                    bg, border, txt, badge = "#bbf7d0", "#22c55e", "#15803d", f"✅ {score}"
                elif score is not None and score >= 60:
                    bg, border, txt, badge = "#fed7aa", "#f97316", "#9a3412", f"✏️ {score}"
                elif score is not None:
                    bg, border, txt, badge = "#fecaca", "#ef4444", "#991b1b", f"⚠️ {score}"
                elif is_learned:
                    bg, border, txt, badge = "#bfdbfe", "#3b82f6", "#1e40af", "📖 已學"
                else:
                    bg, border, txt, badge = "#f3f4f6", "#e5e7eb", "#6b7280", "未開始"
                with cols[idx]:
                    st.markdown(
                        f"<div style='background:{bg};border:1px solid {border};color:{txt};"
                        f"border-radius:8px;padding:8px 2px;text-align:center;margin-bottom:8px;"
                        f"font-family:monospace;box-shadow:0 1px 3px rgba(0,0,0,0.05);'>"
                        f"<div style='font-weight:700;font-size:0.85rem;'>U{u_id:02d}</div>"
                        f"<div style='font-size:0.72rem;font-weight:600;'>{badge}</div></div>",
                        unsafe_allow_html=True
                    )

    with tab_comparison:
        st.markdown("### 🏆 雙寶學習進度對比榜")
        st.caption("方便家長同時檢視 Timmy 與 Chloe 的最新閱讀進度與學習成效！")
        user_list = list(all_users.keys())
        comp_cols = st.columns(max(len(user_list), 2))

        for idx, u_name in enumerate(user_list):
            u_info = all_users[u_name]
            u_comp_units = set(u_info.get("completed_units", []))
            u_scores = {int(k): v for k, v in u_info.get("quiz_scores", {}).items()}
            u_avg = int(sum(u_scores.values()) / len(u_scores)) if u_scores else 0
            u_mastered = sum(1 for s in u_scores.values() if s == 100)
            u_last_u = u_info.get("last_unit", 1)
            u_last_c = u_info.get("last_card_index", 0) + 1
            u_last_time = u_info.get("last_study_time", "")

            with comp_cols[idx]:
                border_color = "#3b82f6" if u_name == current_user else "#e2e8f0"
                active_label = "（目前使用中）" if u_name == current_user else " "
                active_color = "#2563eb" if u_name == current_user else "#64748b"
                st.markdown(
                    f"<div style='background:#ffffff;border:2px solid {border_color};"
                    f"border-radius:14px;padding:20px;text-align:center;"
                    f"box-shadow:0 4px 12px rgba(0,0,0,0.05);margin-bottom:16px;'>"
                    f"<h3 style='margin:0;color:#1e293b;'>{u_name}</h3>"
                    f"<div style='font-size:0.85rem;color:{active_color};font-weight:600;margin-bottom:6px;'>"
                    f"{active_label}</div>"
                    f"<div style='background:#f8fafc;border-radius:8px;padding:6px;margin-bottom:12px;"
                    f"font-size:0.85rem;color:#475569;'>"
                    f"📍 <strong>最後進度：</strong> Unit {u_last_u:02d} 第 {u_last_c} 字<br/>"
                    f"<span style='font-size:0.75rem;color:#94a3b8;'>⏱️ {u_last_time or '尚未開始'}</span></div>"
                    f"<div style='display:flex;justify-content:space-around;margin-top:10px;'>"
                    f"<div><div style='font-size:0.8rem;color:#64748b;'>已學單元</div>"
                    f"<div style='font-size:1.4rem;font-weight:700;color:#2563eb;'>{len(u_comp_units)}</div></div>"
                    f"<div><div style='font-size:0.8rem;color:#64748b;'>測驗均分</div>"
                    f"<div style='font-size:1.4rem;font-weight:700;color:#16a34a;'>{u_avg} 分</div></div>"
                    f"<div><div style='font-size:0.8rem;color:#64748b;'>滿分次數</div>"
                    f"<div style='font-size:1.4rem;font-weight:700;color:#d97706;'>{u_mastered} 次</div></div>"
                    f"</div></div>",
                    unsafe_allow_html=True
                )
                if u_name != current_user:
                    if st.button(f"切換為 {u_name} 視角", key=f"btn_switch_{idx}", use_container_width=True):
                        switch_user(u_name)
                        st.rerun()

    with tab_history:
        st.markdown("### 📝 家長聯絡簿：測驗時間軸與錯題診斷")
        filter_user = st.selectbox(
            "選擇要檢視的孩子",
            options=list(all_users.keys()),
            index=list(all_users.keys()).index(current_user) if current_user in all_users else 0
        )
        target_history = all_users.get(filter_user, {}).get("quiz_history", [])
        if not target_history:
            st.info(f"【{filter_user}】目前尚無測驗紀錄。")
        else:
            for h in target_history:
                u_num = h.get("unit", 1)
                score = h.get("score", 0)
                t_str = h.get("timestamp", "")
                c_cnt = h.get("correct", 0)
                tot = h.get("total", 10)
                wrongs = h.get("wrong_words", [])
                card_border = "#22c55e" if score >= 80 else ("#f59e0b" if score >= 60 else "#ef4444")
                score_color = "#15803d" if score >= 80 else ("#b45309" if score >= 60 else "#b91c1c")
                wrong_html = (
                    f'⚠️ 需多加複習：<strong style="color:#dc2626;">{", ".join(wrongs)}</strong>'
                    if wrongs else "🎉 本次測驗全對！"
                )
                st.markdown(
                    f"<div style='background:#ffffff;border:1px solid #e2e8f0;"
                    f"border-left:5px solid {card_border};border-radius:10px;"
                    f"padding:14px 18px;margin-bottom:10px;'>"
                    f"<div style='display:flex;justify-content:space-between;flex-wrap:wrap;'>"
                    f"<span style='font-weight:700;font-size:1.1rem;color:#1e293b;'>📖 Unit {u_num:02d} 隨堂測驗</span>"
                    f"<span style='font-size:0.85rem;color:#64748b;'>⏱️ {t_str}</span></div>"
                    f"<div style='margin-top:6px;'>得分：<strong style='color:{score_color};"
                    f"font-size:1.25rem;'>{score} 分</strong> "
                    f"<span style='color:#64748b;font-size:0.9rem;'>(答對 {c_cnt}/{tot} 題)</span></div>"
                    f"<div style='margin-top:6px;font-size:0.92rem;color:#475569;'>{wrong_html}</div></div>",
                    unsafe_allow_html=True
                )

    st.markdown("---")
    st.markdown("### 💾 全部小孩進度備份與還原")
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
        st.caption("包含 Timmy 與 Chloe 的所有學習、測驗與最後進度紀錄。")

    with col_imp:
        upload_backup = st.file_uploader("匯入學習進度 (JSON)", type=["json"], key="backup_uploader")
        if upload_backup is not None:
            try:
                loaded = json.load(upload_backup)
                _save_to_github(loaded)
                os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
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
            st.session_state["active_unit"] = 1
            st.session_state["unit_1_card_idx"] = 0
            save_persistent_progress()
            st.warning(f"{current_user} 的學習紀錄已重設！")
            st.rerun()
