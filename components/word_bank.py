"""
Personal Word Bank component.
Allows each user (Timmy / Chloe) to save custom vocabulary words for later review.
Data is stored per-user inside data/user_progress.json under 'my_words'.
"""

import os
import json
import datetime
import streamlit as st
from typing import List, Dict, Any

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "user_progress.json")


def _load_progress_raw() -> Dict:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"current_user": "Timmy", "users": {}}


def _save_progress_raw(data: Dict):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_user_word_bank(user: str) -> List[Dict]:
    """Returns the list of custom words saved by the user."""
    data = _load_progress_raw()
    return data.get("users", {}).get(user, {}).get("my_words", [])


def save_word_to_bank(user: str, word_dict: Dict) -> bool:
    """Adds a new word to the user's word bank. Returns False if word already exists."""
    data = _load_progress_raw()
    if "users" not in data:
        data["users"] = {}
    if user not in data["users"]:
        data["users"][user] = {}
    if "my_words" not in data["users"][user]:
        data["users"][user]["my_words"] = []

    existing_words = [w.get("word", "").strip().lower() for w in data["users"][user]["my_words"]]
    if word_dict.get("word", "").strip().lower() in existing_words:
        return False  # duplicate

    word_dict["added_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    data["users"][user]["my_words"].append(word_dict)
    _save_progress_raw(data)
    return True


def delete_word_from_bank(user: str, word: str):
    """Removes a word from the user's word bank."""
    data = _load_progress_raw()
    my_words = data.get("users", {}).get(user, {}).get("my_words", [])
    data["users"][user]["my_words"] = [w for w in my_words if w.get("word", "").strip().lower() != word.strip().lower()]
    _save_progress_raw(data)


def render_word_bank_page(current_user: str):
    """Renders the full personal word bank page with 3 tabs."""
    st.markdown(f"## 📝 【{current_user}】的個人單字本")
    st.caption("把不熟悉的單字加進來，之後可以用閃卡複習或出測驗題！每個人的單字本完全獨立。")

    tab_add, tab_list, tab_review = st.tabs([
        "➕ 新增單字",
        "📖 單字本列表",
        "🃏 複習 & 測驗"
    ])

    # ── Tab 1: Add Word ──────────────────────────────────────────────
    with tab_add:
        st.markdown("### ➕ 新增不熟悉的單字")
        st.caption("只需填入英文單字和中文意思，其餘為選填。")

        with st.form("add_word_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_word = st.text_input("🔤 英文單字 *（必填）", placeholder="例如：ephemeral")
                new_chinese = st.text_input("🈶 中文意思 *（必填）", placeholder="例如：短暫的")
            with col2:
                new_pos = st.selectbox("詞性（選填）", options=["", "n.", "v.", "adj.", "adv.", "phr.", "prep.", "conj."])
                new_eng = st.text_input("📖 英文解釋（選填）", placeholder="例如：lasting for a very short time")

            new_example = st.text_input("✏️ 例句（選填）", placeholder="例如：The ephemeral beauty of the sunset.")

            submitted = st.form_submit_button("📌 加入我的單字本", use_container_width=True)

            if submitted:
                if not new_word.strip():
                    st.error("請輸入英文單字！")
                elif not new_chinese.strip():
                    st.error("請輸入中文意思！")
                else:
                    word_dict = {
                        "word": new_word.strip(),
                        "pos": new_pos,
                        "chinese_meaning": new_chinese.strip(),
                        "english_definition": new_eng.strip(),
                        "example_sentence": new_example.strip(),
                    }
                    ok = save_word_to_bank(current_user, word_dict)
                    if ok:
                        st.success(f"✅ 「{new_word.strip()}」已加入您的單字本！")
                        st.balloons()
                    else:
                        st.warning(f"「{new_word.strip()}」已在您的單字本中，不重複加入。")

    # ── Tab 2: List View ─────────────────────────────────────────────
    with tab_list:
        my_words = load_user_word_bank(current_user)
        st.markdown(f"### 📖 {current_user} 的單字本（共 {len(my_words)} 字）")

        if not my_words:
            st.info("您的單字本還是空的！切換到「➕ 新增單字」tab 開始加入不熟悉的單字吧。")
        else:
            # Search filter
            search_q = st.text_input("🔍 搜尋單字本", placeholder="輸入英文或中文搜尋", label_visibility="collapsed")
            filtered = my_words
            if search_q.strip():
                q = search_q.strip().lower()
                filtered = [w for w in my_words if q in w.get("word", "").lower() or q in w.get("chinese_meaning", "").lower()]

            st.write("")
            for i, w in enumerate(filtered):
                word = w.get("word", "")
                pos = w.get("pos", "")
                chi = w.get("chinese_meaning", "")
                eng = w.get("english_definition", "")
                example = w.get("example_sentence", "")
                added = w.get("added_at", "")

                with st.container():
                    c1, c2 = st.columns([9, 1])
                    with c1:
                        pos_str = f"<span style='background:#e0f2fe;color:#0369a1;border-radius:4px;padding:1px 6px;font-size:0.8rem;font-weight:600;'>{pos}</span>" if pos else ""
                        eng_str = f"<div style='color:#475569;font-size:0.9rem;margin-top:3px;'>{eng}</div>" if eng else ""
                        ex_str = f"<div style='color:#64748b;font-size:0.85rem;font-style:italic;margin-top:2px;'>✏️ {example}</div>" if example else ""
                        time_str = f"<div style='color:#94a3b8;font-size:0.75rem;margin-top:4px;'>📅 加入時間：{added}</div>" if added else ""
                        st.markdown(f"""
<div style='background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid #6366f1;border-radius:10px;padding:12px 16px;margin-bottom:8px;'>
  <div style='font-size:1.15rem;font-weight:700;color:#1e293b;'>{word} {pos_str}</div>
  <div style='color:#7c3aed;font-weight:600;font-size:1rem;margin-top:2px;'>🈶 {chi}</div>
  {eng_str}{ex_str}{time_str}
</div>""", unsafe_allow_html=True)
                    with c2:
                        st.write("")
                        st.write("")
                        if st.button("🗑️", key=f"del_wb_{i}_{word}", help=f"刪除「{word}」"):
                            delete_word_from_bank(current_user, word)
                            st.success(f"已刪除「{word}」")
                            st.rerun()

    # ── Tab 3: Review & Quiz ─────────────────────────────────────────
    with tab_review:
        my_words = load_user_word_bank(current_user)
        total = len(my_words)
        st.markdown(f"### 🃏 複習模式（共 {total} 個單字）")

        if total == 0:
            st.info("您的單字本還是空的！先去「➕ 新增單字」加入一些不熟悉的單字。")
        else:
            review_mode = st.radio(
                "選擇複習方式",
                options=["🃏 閃卡翻轉複習", "✍️ 選擇題測驗"],
                horizontal=True,
                label_visibility="collapsed"
            )

            if review_mode == "🃏 閃卡翻轉複習":
                _render_wordbank_flashcard(my_words, current_user)
            else:
                if total < 4:
                    st.warning(f"選擇題測驗需要至少 4 個單字，您目前有 {total} 個。請先多加入一些單字！")
                else:
                    _render_wordbank_quiz(my_words, current_user)


def _render_wordbank_flashcard(words: List[Dict], user: str):
    """Renders a simple flashcard review for the word bank."""
    state_key = f"wb_card_idx_{user}"
    flip_key = f"wb_flip_{user}"

    if state_key not in st.session_state:
        st.session_state[state_key] = 0
    if flip_key not in st.session_state:
        st.session_state[flip_key] = False

    idx = st.session_state[state_key] % len(words)
    w = words[idx]

    word = w.get("word", "")
    pos = w.get("pos", "")
    chi = w.get("chinese_meaning", "")
    eng = w.get("english_definition", "")
    example = w.get("example_sentence", "")
    flipped = st.session_state[flip_key]

    st.caption(f"第 {idx + 1} 張 / 共 {len(words)} 張")

    if not flipped:
        st.markdown(f"""
<div style='background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;border-radius:20px;padding:60px 30px;text-align:center;margin:20px 0;box-shadow:0 8px 24px rgba(99,102,241,0.25);'>
  <div style='font-size:2.5rem;font-weight:800;letter-spacing:1px;'>{word}</div>
  <div style='margin-top:10px;font-size:1rem;opacity:0.85;'>{"(" + pos + ")" if pos else ""}</div>
  <div style='margin-top:20px;font-size:1.1rem;opacity:0.9;'>點擊下方按鈕查看中文意思 👇</div>
</div>""", unsafe_allow_html=True)
    else:
        eng_str = f"<div style='color:#475569;font-size:1rem;margin-top:8px;'>📖 {eng}</div>" if eng else ""
        ex_str = f"<div style='color:#64748b;font-size:0.95rem;font-style:italic;margin-top:8px;'>✏️ {example}</div>" if example else ""
        st.markdown(f"""
<div style='background:white;border:2px solid #6366f1;border-radius:20px;padding:50px 30px;text-align:center;margin:20px 0;box-shadow:0 8px 24px rgba(99,102,241,0.1);'>
  <div style='font-size:1.5rem;font-weight:700;color:#6366f1;'>{word} {"(" + pos + ")" if pos else ""}</div>
  <div style='font-size:2rem;font-weight:800;color:#7c3aed;margin-top:12px;'>🈶 {chi}</div>
  {eng_str}{ex_str}
</div>""", unsafe_allow_html=True)

    btn1, btn2, btn3 = st.columns(3)
    with btn1:
        if st.button("⬅ 上一張", use_container_width=True, disabled=(idx <= 0)):
            st.session_state[state_key] = (idx - 1) % len(words)
            st.session_state[flip_key] = False
            st.rerun()
    with btn2:
        label = "🔄 翻面（看答案）" if not flipped else "🔄 翻回（看單字）"
        if st.button(label, use_container_width=True):
            st.session_state[flip_key] = not flipped
            st.rerun()
    with btn3:
        if st.button("下一張 ➡", use_container_width=True, disabled=(idx >= len(words) - 1)):
            st.session_state[state_key] = (idx + 1) % len(words)
            st.session_state[flip_key] = False
            st.rerun()


def _render_wordbank_quiz(words: List[Dict], user: str):
    """Renders a multiple-choice quiz using words from the personal word bank."""
    import random

    quiz_key = f"wb_quiz_{user}"
    submitted_key = f"wb_quiz_submitted_{user}"
    answers_key = f"wb_quiz_answers_{user}"

    if quiz_key not in st.session_state:
        st.session_state[quiz_key] = _generate_wb_quiz(words)
        st.session_state[submitted_key] = False
        st.session_state[answers_key] = {}

    questions = st.session_state[quiz_key]

    col_t1, col_t2 = st.columns([4, 1])
    with col_t2:
        if st.button("🔄 重新出題", use_container_width=True):
            st.session_state[quiz_key] = _generate_wb_quiz(words)
            st.session_state[submitted_key] = False
            st.session_state[answers_key] = {}
            st.rerun()

    is_submitted = st.session_state[submitted_key]

    with st.form(key="wb_quiz_form"):
        for q in questions:
            q_id = q["q_id"]
            st.markdown(f"**第 {q_id} 題：** 請選出與以下中文意思相符的英文單字")
            st.markdown(f"🈶 **{q['chinese_meaning']}**")
            if q.get("english_definition"):
                st.caption(f"📖 提示：{q['english_definition']}")
            ans = st.radio(
                f"Q{q_id} 選項",
                options=q["options"],
                index=None,
                key=f"wb_ans_{user}_{q_id}",
                label_visibility="collapsed"
            )
            st.session_state[answers_key][q_id] = ans
            st.markdown("---")

        submitted = st.form_submit_button("📩 提交答案", use_container_width=True)
        if submitted:
            st.session_state[submitted_key] = True
            st.rerun()

    if is_submitted:
        correct = 0
        wrong_words = []
        for q in questions:
            q_id = q["q_id"]
            user_ans = st.session_state[answers_key].get(q_id)
            if user_ans and user_ans.strip().lower() == q["answer"].strip().lower():
                correct += 1
                st.success(f"第 {q_id} 題 ✅ 正確！答案：**{q['answer']}**")
            else:
                wrong_words.append(q["answer"])
                st.error(f"第 {q_id} 題 ❌ 錯誤。您答：**{user_ans or '未作答'}**，正確答案：**{q['answer']}**")

        score = int(correct / len(questions) * 100)
        st.markdown("---")
        st.markdown(f"### 🎯 得分：**{score} 分**（答對 {correct} / {len(questions)} 題）")
        if score == 100:
            st.balloons()
            st.success("🎉 全對！您的個人單字本單字全部掌握了！")
        elif score >= 80:
            st.success("👍 表現很好！繼續複習幾次就能完全記住！")
        else:
            st.warning(f"需要加強的單字：{', '.join(wrong_words)}")


def _generate_wb_quiz(words: List[Dict]) -> List[Dict]:
    """Generates multiple-choice questions from word bank, options strictly from word bank."""
    import random
    all_words = [w.get("word", "") for w in words]
    sample_size = min(10, len(words))
    selected = random.sample(words, sample_size)
    questions = []
    for i, w in enumerate(selected):
        answer = w.get("word", "")
        distractors = [x for x in all_words if x != answer]
        distractors = random.sample(distractors, min(3, len(distractors)))
        options = distractors + [answer]
        random.shuffle(options)
        questions.append({
            "q_id": i + 1,
            "answer": answer,
            "chinese_meaning": w.get("chinese_meaning", ""),
            "english_definition": w.get("english_definition", ""),
            "options": options,
        })
    return questions
