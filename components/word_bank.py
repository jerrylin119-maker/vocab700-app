"""
Personal Word Bank component.
User types only the English word; system auto-looks up all data.
Words NOT found in either the 700-word DB or the dictionary API are REJECTED (not saved).
Data is stored per-user inside data/user_progress.json under 'my_words'.
"""

import os
import json
import datetime
import urllib.request
import urllib.error
import streamlit as st
from typing import List, Dict, Any

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "user_progress.json")

POS_MAP = {
    "noun": "n.", "verb": "v.", "adjective": "adj.",
    "adverb": "adv.", "preposition": "prep.",
    "conjunction": "conj.", "pronoun": "pron.", "interjection": "int."
}


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
        return False

    word_dict["added_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    data["users"][user]["my_words"].append(word_dict)
    _save_progress_raw(data)
    return True


def delete_word_from_bank(user: str, word: str):
    """Removes a word from the user's word bank."""
    data = _load_progress_raw()
    my_words = data.get("users", {}).get(user, {}).get("my_words", [])
    data["users"][user]["my_words"] = [
        w for w in my_words if w.get("word", "").strip().lower() != word.strip().lower()
    ]
    _save_progress_raw(data)


def _lookup_word(word_str: str) -> tuple:
    """
    Looks up a word. Returns (word_dict, source_label) on success,
    or (None, error_message) if the word cannot be found or is misspelled.
    """
    # 1. Try vocab database
    vocab_data = st.session_state.get("vocab_data", [])
    for entry in vocab_data:
        if entry.get("word", "").strip().lower() == word_str:
            return {
                "word": entry.get("word", word_str),
                "pos": entry.get("pos", ""),
                "chinese_meaning": entry.get("chinese_meaning", ""),
                "english_definition": entry.get("english_definition", ""),
                "example_sentence": entry.get("example_sentence", ""),
            }, "📚 資料來源：700 核心單字資料庫（完整中文意思已自動填入）"

    # 2. Try free dictionary API
    try:
        api_url = "https://api.dictionaryapi.dev/api/v2/entries/en/" + word_str
        req = urllib.request.Request(api_url, headers={"User-Agent": "vocab700-app"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            api_data = json.loads(resp.read())

        if api_data and isinstance(api_data, list) and "word" in api_data[0]:
            entry = api_data[0]
            actual_word = entry.get("word", word_str)
            meanings = entry.get("meanings", [])
            pos_raw = meanings[0].get("partOfSpeech", "") if meanings else ""
            pos_str = POS_MAP.get(pos_raw, pos_raw)
            defs = meanings[0].get("definitions", []) if meanings else []
            eng_def = defs[0].get("definition", "") if defs else ""
            example_raw = defs[0].get("example", "") if defs else ""
            return {
                "word": actual_word,
                "pos": pos_str,
                "chinese_meaning": "",
                "english_definition": eng_def,
                "example_sentence": example_raw,
            }, "🌐 資料來源：英文線上字典（此字不在 700 字庫，中文意思暫無）"

    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Word genuinely not found = likely misspelled
            return None, f"❌ 查無此字「{word_str}」，可能是拼字錯誤。請確認後再試，單字未加入。"
        # Other HTTP error
        return None, f"⚠️ 字典查詢失敗（HTTP {e.code}），單字未加入，請稍後再試。"
    except Exception:
        pass

    # Network error (can't reach API)
    return None, "⚠️ 網路連線失敗，無法確認此字是否正確，單字未加入。請確認網路後再試。"


def _word_preview_html(wd: Dict) -> str:
    """Generates an HTML preview card for a word dict."""
    pos_display = (
        f"<span style='background:#e0f2fe;color:#0369a1;border-radius:4px;"
        f"padding:1px 6px;font-size:0.8rem;font-weight:600;'>{wd['pos']}</span>"
        if wd.get("pos") else ""
    )
    chi = wd.get("chinese_meaning", "")
    chi_display = (
        f"<div style='color:#7c3aed;font-weight:600;font-size:1rem;margin-top:4px;'>🈶 {chi}</div>"
        if chi else
        "<div style='color:#94a3b8;font-size:0.9rem;margin-top:4px;'>中文意思：（此字不在 700 字庫，暫無中文）</div>"
    )
    eng = wd.get("english_definition", "")
    eng_display = (
        f"<div style='color:#475569;font-size:0.9rem;margin-top:4px;'>📖 {eng}</div>" if eng else ""
    )
    ex = wd.get("example_sentence", "")
    ex_display = (
        f"<div style='color:#64748b;font-size:0.85rem;font-style:italic;margin-top:4px;'>✏️ {ex}</div>"
        if ex else ""
    )
    return (
        f"<div style='background:#f0fdf4;border:1px solid #86efac;border-left:4px solid #22c55e;"
        f"border-radius:10px;padding:14px 18px;margin-top:10px;'>"
        f"<div style='font-size:1.2rem;font-weight:700;color:#1e293b;'>{wd['word']} {pos_display}</div>"
        f"{chi_display}{eng_display}{ex_display}</div>"
    )


def render_word_bank_page(current_user: str):
    """Renders the full personal word bank page with 3 tabs."""
    st.markdown(f"## 📝 【{current_user}】的個人單字本")
    st.caption("把不熟悉的單字加進來，之後可以用閃卡複習或出測驗題！每個人的單字本完全獨立。")

    tab_add, tab_list, tab_review = st.tabs([
        "➕ 新增單字",
        "📖 單字本列表",
        "🃏 複習 & 測驗"
    ])

    # ── Tab 1: Add Word (single input, auto-lookup) ──────────────────
    with tab_add:
        st.markdown("### ➕ 新增不熟悉的單字")
        st.caption("只需輸入英文單字，系統會自動查詢詞性、中文意思、英文解釋與例句。拼字錯誤的單字不會被加入。")

        new_word_input = st.text_input(
            "🔤 輸入英文單字",
            placeholder="例如：abandon、persevere、eloquent…",
            key="wb_new_word_input"
        )

        if st.button("🔍 查詢並加入單字本", use_container_width=True, type="primary"):
            word_str = new_word_input.strip().lower()
            if not word_str:
                st.error("請先輸入英文單字！")
            else:
                with st.spinner("查詢中…"):
                    word_dict, source_label = _lookup_word(word_str)

                if word_dict is None:
                    # Word not found anywhere — show error, do NOT save
                    st.error(source_label)
                else:
                    ok = save_word_to_bank(current_user, word_dict)
                    if ok:
                        st.success(f"✅ 「{word_dict['word']}」已加入您的單字本！")
                        st.caption(source_label)
                        st.markdown(_word_preview_html(word_dict), unsafe_allow_html=True)
                        st.balloons()
                    else:
                        st.warning(f"「{word_dict['word']}」已在您的單字本中，不重複加入。")

    # ── Tab 2: List View ─────────────────────────────────────────────
    with tab_list:
        my_words = load_user_word_bank(current_user)
        st.markdown(f"### 📖 {current_user} 的單字本（共 {len(my_words)} 字）")

        if not my_words:
            st.info("您的單字本還是空的！切換到「➕ 新增單字」tab，輸入一個英文單字試試看。")
        else:
            search_q = st.text_input(
                "搜尋", placeholder="🔍 輸入英文或中文搜尋…", label_visibility="collapsed"
            )
            filtered = my_words
            if search_q.strip():
                q = search_q.strip().lower()
                filtered = [
                    w for w in my_words
                    if q in w.get("word", "").lower() or q in w.get("chinese_meaning", "").lower()
                ]

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
                        pos_str = (
                            f"<span style='background:#e0f2fe;color:#0369a1;border-radius:4px;"
                            f"padding:1px 6px;font-size:0.8rem;font-weight:600;'>{pos}</span>"
                            if pos else ""
                        )
                        chi_str = (
                            f"<div style='color:#7c3aed;font-weight:600;font-size:1rem;margin-top:2px;'>🈶 {chi}</div>"
                            if chi else ""
                        )
                        eng_str = (
                            f"<div style='color:#475569;font-size:0.9rem;margin-top:3px;'>📖 {eng}</div>"
                            if eng else ""
                        )
                        ex_str = (
                            f"<div style='color:#64748b;font-size:0.85rem;font-style:italic;margin-top:2px;'>✏️ {example}</div>"
                            if example else ""
                        )
                        time_str = (
                            f"<div style='color:#94a3b8;font-size:0.75rem;margin-top:4px;'>📅 {added}</div>"
                            if added else ""
                        )
                        st.markdown(
                            f"<div style='background:#f8fafc;border:1px solid #e2e8f0;"
                            f"border-left:4px solid #6366f1;border-radius:10px;"
                            f"padding:12px 16px;margin-bottom:8px;'>"
                            f"<div style='font-size:1.15rem;font-weight:700;color:#1e293b;'>"
                            f"{word} {pos_str}</div>"
                            f"{chi_str}{eng_str}{ex_str}{time_str}</div>",
                            unsafe_allow_html=True
                        )
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
                    st.warning(
                        f"選擇題測驗需要至少 4 個單字，您目前有 {total} 個。請先多加入一些單字！"
                    )
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
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;"
            f"border-radius:20px;padding:60px 30px;text-align:center;margin:20px 0;"
            f"box-shadow:0 8px 24px rgba(99,102,241,0.25);'>"
            f"<div style='font-size:2.5rem;font-weight:800;letter-spacing:1px;'>{word}</div>"
            f"<div style='margin-top:10px;font-size:1rem;opacity:0.85;'>{'(' + pos + ')' if pos else ''}</div>"
            f"<div style='margin-top:20px;font-size:1.1rem;opacity:0.9;'>點擊下方按鈕查看中文意思 👇</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    else:
        eng_str = (
            f"<div style='color:#475569;font-size:1rem;margin-top:8px;'>📖 {eng}</div>" if eng else ""
        )
        ex_str = (
            f"<div style='color:#64748b;font-size:0.95rem;font-style:italic;margin-top:8px;'>✏️ {example}</div>"
            if example else ""
        )
        chi_display = chi if chi else "（此字不在 700 字庫，暫無中文）"
        st.markdown(
            f"<div style='background:white;border:2px solid #6366f1;border-radius:20px;"
            f"padding:50px 30px;text-align:center;margin:20px 0;"
            f"box-shadow:0 8px 24px rgba(99,102,241,0.1);'>"
            f"<div style='font-size:1.5rem;font-weight:700;color:#6366f1;'>"
            f"{word} {'(' + pos + ')' if pos else ''}</div>"
            f"<div style='font-size:2rem;font-weight:800;color:#7c3aed;margin-top:12px;'>🈶 {chi_display}</div>"
            f"{eng_str}{ex_str}</div>",
            unsafe_allow_html=True
        )

    btn1, btn2, btn3 = st.columns(3)
    with btn1:
        if st.button("⬅ 上一張", use_container_width=True, disabled=(idx <= 0)):
            st.session_state[state_key] = idx - 1
            st.session_state[flip_key] = False
            st.rerun()
    with btn2:
        label = "🔄 翻面（看答案）" if not flipped else "🔄 翻回（看單字）"
        if st.button(label, use_container_width=True):
            st.session_state[flip_key] = not flipped
            st.rerun()
    with btn3:
        if st.button("下一張 ➡", use_container_width=True, disabled=(idx >= len(words) - 1)):
            st.session_state[state_key] = idx + 1
            st.session_state[flip_key] = False
            st.rerun()


def _render_wordbank_quiz(words: List[Dict], user: str):
    """Renders a multiple-choice quiz using words from the personal word bank."""
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

    with st.form(key=f"wb_quiz_form_{user}"):
        for q in questions:
            q_id = q["q_id"]
            st.markdown(f"**第 {q_id} 題：** 請選出正確的英文單字")
            if q.get("chinese_meaning"):
                st.markdown(f"🈶 **{q['chinese_meaning']}**")
            if q.get("english_definition"):
                st.caption(f"📖 {q['english_definition']}")
            ans = st.radio(
                f"Q{q_id}",
                options=q["options"],
                index=None,
                key=f"wb_ans_{user}_{q_id}",
                label_visibility="collapsed"
            )
            st.session_state[answers_key][q_id] = ans
            st.markdown("---")

        if st.form_submit_button("📩 提交答案", use_container_width=True):
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
                st.success(f"第 {q_id} 題 ✅ 正確！**{q['answer']}**")
            else:
                wrong_words.append(q["answer"])
                st.error(f"第 {q_id} 題 ❌ 正確答案：**{q['answer']}**（您答：{user_ans or '未作答'}）")

        score = int(correct / len(questions) * 100)
        st.markdown("---")
        st.markdown(f"### 🎯 得分：**{score} 分**（{correct} / {len(questions)} 題）")
        if score == 100:
            st.balloons()
            st.success("🎉 全對！個人單字本完全掌握！")
        elif score >= 80:
            st.success("👍 表現很好！再複習幾次就能完全記住！")
        else:
            st.warning(f"需要加強：{', '.join(wrong_words)}")


def _generate_wb_quiz(words: List[Dict]) -> List[Dict]:
    """Generates multiple-choice questions; options strictly from word bank."""
    import random
    all_word_strs = [w.get("word", "") for w in words]
    sample_size = min(10, len(words))
    selected = random.sample(words, sample_size)
    questions = []
    for i, w in enumerate(selected):
        answer = w.get("word", "")
        distractors = [x for x in all_word_strs if x != answer]
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
