"""
Web Speech API TTS component for American English word and sentence pronunciation.
Uses browser native window.speechSynthesis for zero-latency, high-fidelity speech.
"""

import streamlit as st
import streamlit.components.v1 as components
import html

def render_speech_button(text: str, label: str = "🔊 發音", rate: float = 0.95, key: str = None, height: int = 44):
    """
    Renders an inline modern button that triggers browser Web Speech API.
    """
    clean_text = html.escape(text.replace("'", "\\'").replace('"', '\\"'))
    element_id = f"tts_btn_{abs(hash(text + str(rate) + str(key)))}"

    html_code = f"""
    <div style="display: inline-block; margin: 2px 0;">
        <button id="{element_id}" 
                onclick="speakText_{element_id}()" 
                style="
                    background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
                    color: white;
                    border: none;
                    padding: 6px 14px;
                    font-size: 14px;
                    font-weight: 600;
                    border-radius: 8px;
                    cursor: pointer;
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    box-shadow: 0 2px 6px rgba(59, 130, 246, 0.3);
                    transition: all 0.2s ease;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                "
                onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 4px 10px rgba(59, 130, 246, 0.45)';"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 6px rgba(59, 130, 246, 0.3)';"
                onmousedown="this.style.transform='translateY(1px)';"
        >
            <span>{label}</span>
        </button>
    </div>

    <script>
    function speakText_{element_id}() {{
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel(); // Stop any pending speech
            const utterance = new SpeechSynthesisUtterance("{clean_text}");
            utterance.lang = 'en-US';
            utterance.rate = {rate};
            utterance.pitch = 1.0;

            // Attempt to choose an en-US voice
            const voices = window.speechSynthesis.getVoices();
            const usVoice = voices.find(v => v.lang === 'en-US' || v.lang === 'en_US');
            if (usVoice) {{
                utterance.voice = usVoice;
            }}

            window.speechSynthesis.speak(utterance);
        }} else {{
            alert('您的瀏覽器不支援 Web Speech API 語音合成。');
        }}
    }}
    </script>
    """
    components.html(html_code, height=height)

def render_dual_speech_controls(word: str, sentence: str = None, rate: float = 0.95):
    """
    Renders dual pronunciation controls: standard speed and slow speed for single word, plus sentence speech.
    """
    clean_word = html.escape(word.replace("'", "\\'").replace('"', '\\"'))
    clean_sentence = html.escape((sentence or "").replace("'", "\\'").replace('"', '\\"')) if sentence else ""
    element_id = f"ctrl_{abs(hash(word))}"

    sentence_btn = ""
    if sentence:
        sentence_btn = f"""
        <button onclick="playSentence_{element_id}()" 
                style="
                    background: rgba(99, 102, 241, 0.12);
                    color: #4f46e5;
                    border: 1px solid rgba(99, 102, 241, 0.3);
                    padding: 5px 12px;
                    font-size: 13px;
                    font-weight: 500;
                    border-radius: 6px;
                    cursor: pointer;
                    transition: all 0.15s ease;
                "
                onmouseover="this.style.background='rgba(99, 102, 241, 0.2)';"
                onmouseout="this.style.background='rgba(99, 102, 241, 0.12)';"
        >
            🎧 朗讀例句
        </button>
        """

    html_code = f"""
    <div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 6px 0 10px 0;">
        <button onclick="playWord_{element_id}(1.0)" 
                style="
                    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
                    color: white;
                    border: none;
                    padding: 6px 14px;
                    font-size: 14px;
                    font-weight: 600;
                    border-radius: 8px;
                    cursor: pointer;
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
                    transition: all 0.15s ease;
                "
                onmouseover="this.style.transform='scale(1.03)';"
                onmouseout="this.style.transform='scale(1)';"
        >
            🔊 美式發音
        </button>

        <button onclick="playWord_{element_id}(0.75)" 
                style="
                    background: rgba(243, 244, 246, 0.9);
                    color: #374151;
                    border: 1px solid #d1d5db;
                    padding: 6px 12px;
                    font-size: 13px;
                    font-weight: 500;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.15s ease;
                "
                onmouseover="this.style.background='#e5e7eb';"
                onmouseout="this.style.background='rgba(243, 244, 246, 0.9)';"
        >
            🐢 慢速 (0.75x)
        </button>

        {sentence_btn}
    </div>

    <script>
    function playWord_{element_id}(customRate) {{
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance("{clean_word}");
            u.lang = 'en-US';
            u.rate = customRate;
            window.speechSynthesis.speak(u);
        }}
    }}

    function playSentence_{element_id}() {{
        if ('speechSynthesis' in window && "{clean_sentence}") {{
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance("{clean_sentence}");
            u.lang = 'en-US';
            u.rate = 0.9;
            window.speechSynthesis.speak(u);
        }}
    }}
    </script>
    """
    components.html(html_code, height=52)
