"""
Quiz Engine module supporting Multiple Choice and Spelling Fill-in-the-Blank modes.
Handles question generation, scoring, instant evaluation, and explanation review cards.
Features:
- Strict Intra-Unit Options: 100% of multiple-choice options are strictly chosen from the 10 words in the same unit.
"""

import random
import re
import html
import streamlit as st
from typing import List, Dict, Any
from components.audio_player import render_speech_button

def create_masked_sentence(sentence: str, target_word: str) -> str:
    """Replaces occurrences of target word in the sentence with a blank underline `_______`."""
    if not sentence or not target_word:
        return sentence or ""
    try:
        pattern = re.compile(rf"\b{re.escape(target_word)}[a-zA-Z]*\b", re.IGNORECASE)
        return pattern.sub("________", sentence)
    except Exception:
        return sentence

def get_unit_strictly_distractors(target_item: Dict[str, Any], unit_words: List[Dict[str, Any]], count: int = 3) -> List[str]:
    """
    Strictly picks distractors ONLY from the other 9 words in the SAME 10-word unit.
    Prioritizes words with the same Part-of-Speech within the unit.
    """
    target_word = str(target_item.get("word", "")).strip()
    target_pos = str(target_item.get("pos", "")).strip().lower().replace(".", "")

    # Get all other words from the same unit
    other_unit_words = [
        w for w in unit_words 
        if str(w.get("word", "")).strip().lower() != target_word.lower() and str(w.get("word", "")).strip()
    ]

    # Split into same POS vs other POS within this unit
    same_pos = [
        str(w.get("word", "")).strip() for w in other_unit_words 
        if str(w.get("pos", "")).strip().lower().replace(".", "") == target_pos
    ]
    other_pos = [
        str(w.get("word", "")).strip() for w in other_unit_words 
        if str(w.get("word", "")).strip() not in same_pos
    ]

    random.shuffle(same_pos)
    random.shuffle(other_pos)

    # Combine: same-pos in unit first, then other words in unit
    candidate_pool = same_pos + other_pos

    chosen = []
    for w in candidate_pool:
        if w and w.lower() != target_word.lower() and w not in chosen:
            chosen.append(w)
            if len(chosen) >= count:
                break

    return chosen[:count]

def generate_unit_quiz(unit_words: List[Dict[str, Any]], full_dataset: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Generates a 10-question mixed quiz for a given unit.
    ALL multiple choice options are 100% strictly chosen from the 10 words in this unit!
    """
    if not unit_words:
        return []

    questions = []
    words_pool = list(unit_words)
    random.shuffle(words_pool)

    for idx, item in enumerate(words_pool):
        target_word = str(item.get("word", "")).strip()
        pos = str(item.get("pos", "")).strip()
        phonetic = str(item.get("phonetic", "")).strip()
        chi = str(item.get("chinese_meaning", "")).strip()
        eng = str(item.get("english_definition", "")).strip()
        sentence = str(item.get("example_sentence", "")).strip()
        masked_sentence = create_masked_sentence(sentence, target_word)

        # Distribute question types
        q_type_mod = idx % 3
        if q_type_mod == 0:
            q_type = "choice_def"
        elif q_type_mod == 1:
            q_type = "choice_sentence"
        else:
            q_type = "spelling"

        if q_type in ["choice_def", "choice_sentence"]:
            # Strictly pull 3 distractors from the other 9 words in the same unit
            distractors = get_unit_strictly_distractors(item, unit_words, count=3)
            options = distractors + [target_word]
            random.shuffle(options)
        else:
            options = []

        q_dict = {
            "q_id": idx + 1,
            "type": q_type,
            "target_word": target_word,
            "pos": pos,
            "phonetic": phonetic,
            "chinese_meaning": chi,
            "english_definition": eng,
            "sentence": sentence,
            "masked_sentence": masked_sentence,
            "options": options
        }
        questions.append(q_dict)

    return questions

def render_quiz_view(unit_words: List[Dict[str, Any]], full_dataset: List[Dict[str, Any]], unit_id: int):
    """Renders the interactive quiz interface with submission and detailed explanation."""
    st.markdown(f"## ✍️ Unit {unit_id} 隨堂測驗")
    st.caption("測驗包含「單字釋義選擇題」、「例句挖空選擇題」與「拼字填空題」，選擇題選項皆由本單元 10 個單字打散出題。")

    quiz_state_key = f"quiz_questions_unit_{unit_id}"
    quiz_submitted_key = f"quiz_submitted_unit_{unit_id}"
    user_answers_key = f"quiz_answers_unit_{unit_id}"

    unit_word_set = set(str(w.get("word", "")).strip().lower() for w in unit_words if w.get("word"))

    # Force regenerate if not present OR if options in cached quiz contain external words from old session
    need_regenerate = False
    if quiz_state_key not in st.session_state:
        need_regenerate = True
    else:
        existing_q = st.session_state.get(quiz_state_key, [])
        if not existing_q:
            need_regenerate = True
        else:
            # Check if any choice option is not in unit_word_set (i.e. old cached quiz)
            for q in existing_q:
                if q.get("type") in ["choice_def", "choice_sentence"]:
                    for opt in q.get("options", []):
                        if opt.lower() not in unit_word_set:
                            need_regenerate = True
                            break

    if need_regenerate:
        st.session_state[quiz_state_key] = generate_unit_quiz(unit_words, full_dataset)
        st.session_state[quiz_submitted_key] = False
        st.session_state[user_answers_key] = {}

    questions = st.session_state.get(quiz_state_key, [])
    is_submitted = st.session_state.get(quiz_submitted_key, False)

    # Re-generate quiz button
    col_t1, col_t2 = st.columns([3, 1])
    with col_t2:
        if st.button("🔄 重新出題 (New Quiz)", use_container_width=True):
            st.session_state[quiz_state_key] = generate_unit_quiz(unit_words, full_dataset)
            st.session_state[quiz_submitted_key] = False
            st.session_state[user_answers_key] = {}
            st.rerun()

    # Form for quiz answering
    with st.form(key=f"quiz_form_unit_{unit_id}"):
        for q in questions:
            q_id = q.get("q_id", 1)
            q_type = q.get("type", "choice_def")
            target_word = q.get("target_word", "")
            pos = q.get("pos", "")
            chi = q.get("chinese_meaning", "")
            eng = q.get("english_definition", "")
            masked = q.get("masked_sentence", "")
            options = q.get("options", [])

            st.markdown(f"""
            <div class="quiz-question-box">
                <div style="font-weight: 700; color: #1e293b; margin-bottom: 6px;">
                    第 {q_id} 題 / 共 {len(questions)} 題 
                    <span class="quiz-type-tag">
                        {'選擇題 (釋義)' if q_type == 'choice_def' else ('選擇題 (例句)' if q_type == 'choice_sentence' else '拼字填空題')}
                    </span>
                </div>
            """, unsafe_allow_html=True)

            if q_type == "choice_def":
                st.markdown(f"**題幹釋義：** `{eng}` (詞性: **{pos}** / 中文提示: **{chi}**)")
                st.markdown("**請選出最符合釋義的英文單字：**")
                ans = st.radio(
                    f"Q{q_id} 選擇選項",
                    options=options,
                    index=None,
                    key=f"ans_{unit_id}_{q_id}",
                    label_visibility="collapsed"
                )
                st.session_state[user_answers_key][q_id] = ans

            elif q_type == "choice_sentence":
                st.markdown(f"**例句填空：** “{masked}”")
                st.markdown(f"*(中文提示：{chi} | 詞性: {pos})*")
                st.markdown("**請選出最合適填入空格的單字：**")
                ans = st.radio(
                    f"Q{q_id} 例句選項",
                    options=options,
                    index=None,
                    key=f"ans_{unit_id}_{q_id}",
                    label_visibility="collapsed"
                )
                st.session_state[user_answers_key][q_id] = ans

            elif q_type == "spelling":
                first_letter = target_word[0].upper() if target_word else "A"
                st.markdown(f"**句子挖空：** “{masked}”")
                st.markdown(f"**提示：** 中文意思為「**{chi}**」(詞性: `{pos}`)，首字母為 `{first_letter}`，共 {len(target_word)} 個字母")
                ans = st.text_input(
                    f"Q{q_id} 請手動輸入正確拼字：",
                    placeholder="請在此輸入英文單字...",
                    key=f"ans_{unit_id}_{q_id}"
                )
                st.session_state[user_answers_key][q_id] = ans

            st.markdown("</div>", unsafe_allow_html=True)

        submit_btn = st.form_submit_button("🚀 提交測驗 (Submit Quiz)", use_container_width=True, type="primary")
        if submit_btn:
            st.session_state[quiz_submitted_key] = True
            st.rerun()

    # Results view
    if is_submitted:
        st.markdown("---")
        render_quiz_results(unit_id, questions, st.session_state.get(user_answers_key, {}))

def render_quiz_results(unit_id: int, questions: List[Dict[str, Any]], user_answers: Dict[int, Any]):
    """Renders score calculation, evaluation badges, and in-depth explanation cards."""
    if not questions:
        st.warning("測驗資料為空。")
        return

    correct_count = 0
    total_q = max(1, len(questions))
    wrong_words = []
    detailed_eval = []

    for q in questions:
        q_id = q.get("q_id", 1)
        target = str(q.get("target_word", "")).strip()
        user_ans = str(user_answers.get(q_id, "") or "").strip()

        is_correct = bool(user_ans and target and (user_ans.lower() == target.lower()))
        if is_correct:
            correct_count += 1
        else:
            if target:
                wrong_words.append(target)

        detailed_eval.append({
            "q": q,
            "user_ans": user_ans,
            "is_correct": is_correct,
            "target": target
        })

    score_pct = int((correct_count / total_q) * 100)

    # Check high score safely
    quiz_scores = st.session_state.get("quiz_scores", {})
    prev_high = quiz_scores.get(unit_id, 0)
    is_new_high = bool(score_pct > prev_high)

    # Save to history & persistence
    try:
        from components.progress_tracker import record_quiz_attempt
        record_quiz_attempt(unit_id, score_pct, correct_count, total_q, wrong_words)
    except Exception as err:
        print(f"Error recording quiz attempt: {err}")

    # Summary texts
    if score_pct == 100:
        summary_msg = "🏆 完美掌握！表現非常優異！"
        score_color = "#16a34a"
    elif score_pct >= 80:
        summary_msg = "🌟 表現優良！已熟練掌握本單元單字！"
        score_color = "#16a34a"
    elif score_pct >= 60:
        summary_msg = "💪 尚可，建議多複習錯題後再次挑戰！"
        score_color = "#d97706"
    else:
        summary_msg = "⚠️ 建議回到單字卡模式重新學習本單元！"
        score_color = "#dc2626"

    new_record_tag = " (🎉 創下新紀錄！)" if is_new_high else ""
    current_high_score = st.session_state.get("quiz_scores", {}).get(unit_id, score_pct)

    # Render Summary Card
    st.markdown(f"""
    <div class="quiz-score-card">
        <h2 style="margin: 0; color: #1e3a8a;">🎯 測驗結果結算</h2>
        <div style="font-size: 2.5rem; font-weight: 800; color: {score_color}; margin: 8px 0;">
            {score_pct}% <span style="font-size: 1.1rem; color: #64748b; font-weight: 500;">({correct_count} / {total_q} 題答對)</span>
        </div>
        <p style="margin: 0; font-size: 1rem; color: #334155;">{summary_msg}</p>
        <div style="margin-top: 8px; font-size: 0.9rem; color: #64748b;">
            Unit {unit_id} 歷史最高分：<strong>{current_high_score}%</strong>{new_record_tag}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if score_pct >= 80:
        st.balloons()

    # Render Explanation Cards
    st.markdown("### 📝 逐題解析與發音檢視")

    for item in detailed_eval:
        q = item.get("q", {})
        is_correct = item.get("is_correct", False)
        user_ans = item.get("user_ans", "")
        target = item.get("target", "")
        pos = q.get("pos", "")
        phonetic = q.get("phonetic", "")
        chi = q.get("chinese_meaning", "")
        eng = q.get("english_definition", "")
        sentence = q.get("sentence", "")
        masked_s = q.get("masked_sentence", "")

        badge_class = "result-correct" if is_correct else "result-wrong"
        badge_text = "✅ 答對 Correct" if is_correct else "❌ 答錯 Incorrect"
        pos_cls = pos.lower().replace(".", "")
        ans_color = "#16a34a" if is_correct else "#dc2626"

        with st.container():
            explanation_html = f"""<div class="explanation-box {badge_class}"><div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;"><span style="font-weight: 700; font-size: 1.05rem;">第 {q.get('q_id', 1)} 題：{html.escape(masked_s)}</span><span class="status-badge {badge_class}">{badge_text}</span></div><div style="margin: 6px 0; font-size: 0.95rem;"><strong>您的作答：</strong> <span style="color: {ans_color}; font-weight: 600;">{html.escape(user_ans or '(未作答)')}</span>&nbsp;&nbsp;|&nbsp;&nbsp;<strong>正確答案：</strong> <span style="color: #2563eb; font-weight: 700; font-size: 1.1rem;">{html.escape(target)}</span> <span class="pos-badge pos-{pos_cls}">{pos}</span> <span style="color: #64748b; font-family: monospace;">{phonetic}</span></div><div style="color: #334155; margin-top: 4px;"><strong>中文釋義：</strong> {html.escape(chi)} &nbsp;|&nbsp; <strong>英英解釋：</strong> {html.escape(eng)}</div><div style="color: #475569; margin-top: 4px; font-style: italic;"><strong>完整例句：</strong> “{html.escape(sentence)}”</div></div>"""
            st.markdown(explanation_html, unsafe_allow_html=True)

            # Audio Pronunciation Button for target word
            render_speech_button(text=target, label=f"🔊 發音 {target}", rate=0.95, key=f"res_tts_{unit_id}_{q.get('q_id', 1)}", height=38)
            st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)
