"""
Quiz Engine module supporting Multiple Choice and Spelling Fill-in-the-Blank modes.
Handles question generation, scoring, instant evaluation, and explanation review cards.
"""

import random
import re
import streamlit as st
from typing import List, Dict, Any, Tuple
from components.audio_player import render_speech_button
from components.progress_tracker import record_quiz_attempt

def create_masked_sentence(sentence: str, target_word: str) -> str:
    """Replaces occurrences of target word in the sentence with a blank underline `_______`."""
    if not sentence or not target_word:
        return sentence
    pattern = re.compile(rf"\b{re.escape(target_word)}[a-zA-Z]*\b", re.IGNORECASE)
    return pattern.sub("________", sentence)

def generate_unit_quiz(unit_words: List[Dict[str, Any]], full_dataset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generates a 10-question mixed quiz for a given unit.
    Mixed question types:
    1. 'choice_def': Multiple Choice from English Definition
    2. 'choice_sentence': Multiple Choice from Sentence with Blank
    3. 'spelling': Fill-in-the-blank spelling from sentence + Chinese hint
    """
    questions = []
    # All candidate distractor words from full dataset
    all_words = [w["word"] for w in full_dataset if w.get("word")]

    # Shuffle unit words
    words_pool = list(unit_words)
    random.shuffle(words_pool)

    # Assign question types across the words
    # Half choice, half spelling
    for idx, item in enumerate(words_pool):
        target_word = item.get("word", "")
        pos = item.get("pos", "")
        phonetic = item.get("phonetic", "")
        chi = item.get("chinese_meaning", "")
        eng = item.get("english_definition", "")
        sentence = item.get("example_sentence", "")
        masked_sentence = create_masked_sentence(sentence, target_word)

        # Distribute question types evenly
        q_type_mod = idx % 3
        if q_type_mod == 0:
            q_type = "choice_def"
        elif q_type_mod == 1:
            q_type = "choice_sentence"
        else:
            q_type = "spelling"

        # Generate 4 options for multiple choice
        if q_type in ["choice_def", "choice_sentence"]:
            # Pick 3 random distinct distractors
            distractors = [w for w in all_words if w.lower() != target_word.lower()]
            sampled_distractors = random.sample(distractors, min(3, len(distractors)))
            options = sampled_distractors + [target_word]
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
    st.caption("測驗包含「單字釋義選擇題」、「例句挖空選擇題」與「拼字填空題」，共 10 題。")

    quiz_state_key = f"quiz_questions_unit_{unit_id}"
    quiz_submitted_key = f"quiz_submitted_unit_{unit_id}"
    user_answers_key = f"quiz_answers_unit_{unit_id}"

    # Initialize quiz questions if not present
    if quiz_state_key not in st.session_state:
        st.session_state[quiz_state_key] = generate_unit_quiz(unit_words, full_dataset)
        st.session_state[quiz_submitted_key] = False
        st.session_state[user_answers_key] = {}

    questions = st.session_state[quiz_state_key]
    is_submitted = st.session_state[quiz_submitted_key]

    # Action buttons at top: Start over / Re-generate
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
            q_id = q["q_id"]
            q_type = q["type"]
            target_word = q["target_word"]
            pos = q["pos"]
            chi = q["chinese_meaning"]
            eng = q["english_definition"]
            masked = q["masked_sentence"]
            options = q["options"]

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
                st.markdown(f"**句子挖空：** “{masked}”")
                st.markdown(f"**提示：** 中文意思為「**{chi}**」(詞性: `{pos}`)，首字母為 `{target_word[0].upper()}`，共 {len(target_word)} 個字母")
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

    # If quiz is submitted, render results and full detailed explanations
    if is_submitted:
        st.markdown("---")
        render_quiz_results(unit_id, questions, st.session_state[user_answers_key])

def render_quiz_results(unit_id: int, questions: List[Dict[str, Any]], user_answers: Dict[int, Any]):
    """Renders score calculation, evaluation badges, and in-depth explanation cards."""
    correct_count = 0
    total_q = len(questions)
    wrong_words = []

    detailed_eval = []
    for q in questions:
        q_id = q["q_id"]
        target = q["target_word"].strip()
        user_ans = str(user_answers.get(q_id, "") or "").strip()

        # Case-insensitive comparison
        is_correct = (user_ans.lower() == target.lower())
        if is_correct:
            correct_count += 1
        else:
            wrong_words.append(target)

        detailed_eval.append({
            "q": q,
            "user_ans": user_ans,
            "is_correct": is_correct,
            "target": target
        })

    score_pct = int((correct_count / total_q) * 100)

    # Check if this score is a new high record for this unit
    prev_high = st.session_state.get("quiz_scores", {}).get(unit_id, 0)
    is_new_high = bool(score_pct > prev_high)

    # Record quiz attempt to persistent log and update high score
    record_quiz_attempt(unit_id, score_pct, correct_count, total_q, wrong_words)

    # Pre-calculate display strings
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
    high_score_val = st.session_state.get("quiz_scores", {}).get(unit_id, score_pct)

    # Summary Card HTML
    summary_card_html = f"""<div class="quiz-score-card"><h2 style="margin: 0; color: #1e3a8a;">🎯 測驗結果結算</h2><div style="font-size: 2.5rem; font-weight: 800; color: {score_color}; margin: 8px 0;">{score_pct}% <span style="font-size: 1.1rem; color: #64748b; font-weight: 500;">({correct_count} / {total_q} 題答對)</span></div><p style="margin: 0; font-size: 1rem; color: #334155;">{summary_msg}</p><div style="margin-top: 8px; font-size: 0.9rem; color: #64748b;">Unit {unit_id} 歷史最高分：<strong>{high_score_val}%</strong>{new_record_tag}</div></div>"""
    st.markdown(summary_card_html, unsafe_allow_html=True)

    if score_pct >= 80:
        st.balloons()

    # Render Detailed Explanation Cards
    st.markdown("### 📝 逐題解析與發音檢視")

    for item in detailed_eval:
        q = item["q"]
        is_correct = item["is_correct"]
        user_ans = item["user_ans"]
        target = item["target"]
        pos = q["pos"]
        phonetic = q["phonetic"]
        chi = q["chinese_meaning"]
        eng = q["english_definition"]
        sentence = q["sentence"]

        badge_class = "result-correct" if is_correct else "result-wrong"
        badge_text = "✅ 答對 Correct" if is_correct else "❌ 答錯 Incorrect"
        pos_cls = pos.lower().replace(".", "")
        ans_color = "#16a34a" if is_correct else "#dc2626"

        with st.container():
            explanation_html = f"""<div class="explanation-box {badge_class}"><div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;"><span style="font-weight: 700; font-size: 1.05rem;">第 {q['q_id']} 題：{q['masked_sentence']}</span><span class="status-badge {badge_class}">{badge_text}</span></div><div style="margin: 6px 0; font-size: 0.95rem;"><strong>您的作答：</strong> <span style="color: {ans_color}; font-weight: 600;">{user_ans or '(未作答)'}</span>&nbsp;&nbsp;|&nbsp;&nbsp;<strong>正確答案：</strong> <span style="color: #2563eb; font-weight: 700; font-size: 1.1rem;">{target}</span> <span class="pos-badge pos-{pos_cls}">{pos}</span> <span style="color: #64748b; font-family: monospace;">{phonetic}</span></div><div style="color: #334155; margin-top: 4px;"><strong>中文釋義：</strong> {chi} &nbsp;|&nbsp; <strong>英英解釋：</strong> {eng}</div><div style="color: #475569; margin-top: 4px; font-style: italic;"><strong>完整例句：</strong> “{sentence}”</div></div>"""
            st.markdown(explanation_html, unsafe_allow_html=True)

            # Audio Pronunciation Button for target word
            render_speech_button(text=target, label=f"🔊 發音 {target}", rate=0.95, key=f"res_tts_{unit_id}_{q['q_id']}", height=38)
            st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)
