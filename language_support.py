"""
language_support.py
===================

HireSense AI - Multi-Language Support Module

Provides support for conducting interviews in multiple languages:
- Language selection for interview questions and responses
- Localized UI text
- Language-specific TTS voices
- Translation support for reports
"""

from typing import Dict, List, Optional, Tuple
import json

# ============================================================================
# Supported Languages
# ============================================================================

SUPPORTED_LANGUAGES = {
    "en": {
        "name": "English",
        "native_name": "English",
        "flag": "🇺🇸",
        "tts_lang": "en-US",
        "speech_lang": "en-US",
        "direction": "ltr"
    },
    "es": {
        "name": "Spanish",
        "native_name": "Español",
        "flag": "🇪🇸",
        "tts_lang": "es-ES",
        "speech_lang": "es-ES",
        "direction": "ltr"
    },
    "fr": {
        "name": "French",
        "native_name": "Français",
        "flag": "🇫🇷",
        "tts_lang": "fr-FR",
        "speech_lang": "fr-FR",
        "direction": "ltr"
    },
    "de": {
        "name": "German",
        "native_name": "Deutsch",
        "flag": "🇩🇪",
        "tts_lang": "de-DE",
        "speech_lang": "de-DE",
        "direction": "ltr"
    },
    "zh": {
        "name": "Chinese (Mandarin)",
        "native_name": "中文",
        "flag": "🇨🇳",
        "tts_lang": "zh-CN",
        "speech_lang": "zh-CN",
        "direction": "ltr"
    },
    "ja": {
        "name": "Japanese",
        "native_name": "日本語",
        "flag": "🇯🇵",
        "tts_lang": "ja-JP",
        "speech_lang": "ja-JP",
        "direction": "ltr"
    },
    "ko": {
        "name": "Korean",
        "native_name": "한국어",
        "flag": "🇰🇷",
        "tts_lang": "ko-KR",
        "speech_lang": "ko-KR",
        "direction": "ltr"
    },
    "hi": {
        "name": "Hindi",
        "native_name": "हिन्दी",
        "flag": "🇮🇳",
        "tts_lang": "hi-IN",
        "speech_lang": "hi-IN",
        "direction": "ltr"
    },
    "pt": {
        "name": "Portuguese",
        "native_name": "Português",
        "flag": "🇧🇷",
        "tts_lang": "pt-BR",
        "speech_lang": "pt-BR",
        "direction": "ltr"
    },
    "ar": {
        "name": "Arabic",
        "native_name": "العربية",
        "flag": "🇸🇦",
        "tts_lang": "ar-SA",
        "speech_lang": "ar-SA",
        "direction": "rtl"
    },
    "ru": {
        "name": "Russian",
        "native_name": "Русский",
        "flag": "🇷🇺",
        "tts_lang": "ru-RU",
        "speech_lang": "ru-RU",
        "direction": "ltr"
    },
    "it": {
        "name": "Italian",
        "native_name": "Italiano",
        "flag": "🇮🇹",
        "tts_lang": "it-IT",
        "speech_lang": "it-IT",
        "direction": "ltr"
    },
    "ur": {
        "name": "Urdu",
        "native_name": "اردو",
        "flag": "🇵🇰",
        "tts_lang": "ur-PK",
        "speech_lang": "ur-PK",
        "direction": "rtl"
    }
}

# ============================================================================
# UI Translations
# ============================================================================

UI_TRANSLATIONS = {
    "en": {
        "app_title": "HireSense AI",
        "app_subtitle": "Intelligent Interview Platform",
        "setup_session": "Setup Your HireSense Session",
        "select_interview_type": "Select Interview Type",
        "upload_resume": "Upload Your Resume",
        "job_description": "Job Description",
        "session_settings": "Session Settings",
        "num_questions": "Number of Questions",
        "enable_voice": "Enable Voice (TTS)",
        "enable_webcam": "Enable Webcam",
        "enable_voice_input": "Enable Voice Input",
        "start_session": "Start HireSense Session",
        "your_response": "Your Response",
        "submit_answer": "Submit Answer",
        "skip_question": "Skip Question",
        "end_session": "End Session",
        "session_complete": "HireSense Session Complete!",
        "performance_analytics": "HireSense Performance Analytics",
        "ai_report": "HireSense AI Report",
        "generate_report": "Generate HireSense Report",
        "view_report": "View HireSense Report",
        "full_transcript": "Full Session Transcript",
        "start_new_session": "Start New HireSense Session",
        "question_bank": "Question Bank",
        "interview": "Interview",
        "live_status": "Live Status",
        "emotional_state": "Emotional State",
        "ai_mode": "AI Mode",
        "session_stats": "Session Stats",
        "duration": "Duration",
        "exchanges": "Exchanges",
        "confident": "Confident",
        "stressed": "Stressed",
        "neutral": "Neutral",
        "supportive_mode": "Supportive Mode",
        "challenge_mode": "Challenge Mode",
        "balanced_mode": "Balanced Mode",
        "speak_your_answer": "Speak Your Answer",
        "use_this_answer": "Use This Answer",
        "select_language": "Select Language",
        "language": "Language"
    },
    "es": {
        "app_title": "HireSense AI",
        "app_subtitle": "Plataforma de Entrevistas Inteligente",
        "setup_session": "Configura tu Sesión HireSense",
        "select_interview_type": "Selecciona el Tipo de Entrevista",
        "upload_resume": "Sube tu Currículum",
        "job_description": "Descripción del Puesto",
        "session_settings": "Configuración de Sesión",
        "num_questions": "Número de Preguntas",
        "enable_voice": "Habilitar Voz (TTS)",
        "enable_webcam": "Habilitar Cámara",
        "enable_voice_input": "Habilitar Entrada de Voz",
        "start_session": "Iniciar Sesión HireSense",
        "your_response": "Tu Respuesta",
        "submit_answer": "Enviar Respuesta",
        "skip_question": "Saltar Pregunta",
        "end_session": "Terminar Sesión",
        "session_complete": "¡Sesión HireSense Completada!",
        "performance_analytics": "Análisis de Rendimiento HireSense",
        "ai_report": "Informe HireSense AI",
        "generate_report": "Generar Informe HireSense",
        "view_report": "Ver Informe HireSense",
        "full_transcript": "Transcripción Completa",
        "start_new_session": "Iniciar Nueva Sesión HireSense",
        "question_bank": "Banco de Preguntas",
        "interview": "Entrevista",
        "live_status": "Estado en Vivo",
        "emotional_state": "Estado Emocional",
        "ai_mode": "Modo IA",
        "session_stats": "Estadísticas de Sesión",
        "duration": "Duración",
        "exchanges": "Intercambios",
        "confident": "Confiado",
        "stressed": "Estresado",
        "neutral": "Neutral",
        "supportive_mode": "Modo de Apoyo",
        "challenge_mode": "Modo Desafío",
        "balanced_mode": "Modo Equilibrado",
        "speak_your_answer": "Habla tu Respuesta",
        "use_this_answer": "Usar Esta Respuesta",
        "select_language": "Seleccionar Idioma",
        "language": "Idioma"
    },
    "fr": {
        "app_title": "HireSense AI",
        "app_subtitle": "Plateforme d'Entretien Intelligente",
        "setup_session": "Configurez votre Session HireSense",
        "select_interview_type": "Sélectionnez le Type d'Entretien",
        "upload_resume": "Téléchargez votre CV",
        "job_description": "Description du Poste",
        "session_settings": "Paramètres de Session",
        "num_questions": "Nombre de Questions",
        "enable_voice": "Activer la Voix (TTS)",
        "enable_webcam": "Activer la Webcam",
        "enable_voice_input": "Activer l'Entrée Vocale",
        "start_session": "Démarrer la Session HireSense",
        "your_response": "Votre Réponse",
        "submit_answer": "Soumettre la Réponse",
        "skip_question": "Passer la Question",
        "end_session": "Terminer la Session",
        "session_complete": "Session HireSense Terminée!",
        "performance_analytics": "Analyse de Performance HireSense",
        "ai_report": "Rapport HireSense AI",
        "generate_report": "Générer le Rapport HireSense",
        "view_report": "Voir le Rapport HireSense",
        "full_transcript": "Transcription Complète",
        "start_new_session": "Démarrer une Nouvelle Session",
        "question_bank": "Banque de Questions",
        "interview": "Entretien",
        "live_status": "Statut en Direct",
        "emotional_state": "État Émotionnel",
        "ai_mode": "Mode IA",
        "session_stats": "Statistiques de Session",
        "duration": "Durée",
        "exchanges": "Échanges",
        "confident": "Confiant",
        "stressed": "Stressé",
        "neutral": "Neutre",
        "supportive_mode": "Mode Soutien",
        "challenge_mode": "Mode Défi",
        "balanced_mode": "Mode Équilibré",
        "speak_your_answer": "Parlez votre Réponse",
        "use_this_answer": "Utiliser Cette Réponse",
        "select_language": "Sélectionner la Langue",
        "language": "Langue"
    },
    "de": {
        "app_title": "HireSense AI",
        "app_subtitle": "Intelligente Interview-Plattform",
        "setup_session": "Richten Sie Ihre HireSense-Sitzung ein",
        "select_interview_type": "Wählen Sie den Interview-Typ",
        "upload_resume": "Laden Sie Ihren Lebenslauf hoch",
        "job_description": "Stellenbeschreibung",
        "session_settings": "Sitzungseinstellungen",
        "num_questions": "Anzahl der Fragen",
        "enable_voice": "Sprache aktivieren (TTS)",
        "enable_webcam": "Webcam aktivieren",
        "enable_voice_input": "Spracheingabe aktivieren",
        "start_session": "HireSense-Sitzung starten",
        "your_response": "Ihre Antwort",
        "submit_answer": "Antwort senden",
        "skip_question": "Frage überspringen",
        "end_session": "Sitzung beenden",
        "session_complete": "HireSense-Sitzung abgeschlossen!",
        "performance_analytics": "HireSense Leistungsanalyse",
        "ai_report": "HireSense AI-Bericht",
        "generate_report": "HireSense-Bericht erstellen",
        "view_report": "HireSense-Bericht anzeigen",
        "full_transcript": "Vollständiges Transkript",
        "start_new_session": "Neue HireSense-Sitzung starten",
        "question_bank": "Fragenbank",
        "interview": "Interview",
        "live_status": "Live-Status",
        "emotional_state": "Emotionaler Zustand",
        "ai_mode": "KI-Modus",
        "session_stats": "Sitzungsstatistiken",
        "duration": "Dauer",
        "exchanges": "Austausch",
        "confident": "Selbstbewusst",
        "stressed": "Gestresst",
        "neutral": "Neutral",
        "supportive_mode": "Unterstützungsmodus",
        "challenge_mode": "Herausforderungsmodus",
        "balanced_mode": "Ausgeglichener Modus",
        "speak_your_answer": "Sprechen Sie Ihre Antwort",
        "use_this_answer": "Diese Antwort verwenden",
        "select_language": "Sprache auswählen",
        "language": "Sprache"
    },
    "zh": {
        "app_title": "HireSense AI",
        "app_subtitle": "智能面试平台",
        "setup_session": "设置您的HireSense会话",
        "select_interview_type": "选择面试类型",
        "upload_resume": "上传您的简历",
        "job_description": "职位描述",
        "session_settings": "会话设置",
        "num_questions": "问题数量",
        "enable_voice": "启用语音 (TTS)",
        "enable_webcam": "启用摄像头",
        "enable_voice_input": "启用语音输入",
        "start_session": "开始HireSense会话",
        "your_response": "您的回答",
        "submit_answer": "提交回答",
        "skip_question": "跳过问题",
        "end_session": "结束会话",
        "session_complete": "HireSense会话完成！",
        "performance_analytics": "HireSense表现分析",
        "ai_report": "HireSense AI报告",
        "generate_report": "生成HireSense报告",
        "view_report": "查看HireSense报告",
        "full_transcript": "完整记录",
        "start_new_session": "开始新的HireSense会话",
        "question_bank": "题库",
        "interview": "面试",
        "live_status": "实时状态",
        "emotional_state": "情绪状态",
        "ai_mode": "AI模式",
        "session_stats": "会话统计",
        "duration": "时长",
        "exchanges": "交流次数",
        "confident": "自信",
        "stressed": "紧张",
        "neutral": "中立",
        "supportive_mode": "支持模式",
        "challenge_mode": "挑战模式",
        "balanced_mode": "平衡模式",
        "speak_your_answer": "说出您的回答",
        "use_this_answer": "使用此回答",
        "select_language": "选择语言",
        "language": "语言"
    },
    "ja": {
        "app_title": "HireSense AI",
        "app_subtitle": "インテリジェント面接プラットフォーム",
        "setup_session": "HireSenseセッションを設定",
        "select_interview_type": "面接タイプを選択",
        "upload_resume": "履歴書をアップロード",
        "job_description": "職務内容",
        "session_settings": "セッション設定",
        "num_questions": "質問数",
        "enable_voice": "音声を有効化 (TTS)",
        "enable_webcam": "ウェブカメラを有効化",
        "enable_voice_input": "音声入力を有効化",
        "start_session": "HireSenseセッションを開始",
        "your_response": "あなたの回答",
        "submit_answer": "回答を送信",
        "skip_question": "質問をスキップ",
        "end_session": "セッションを終了",
        "session_complete": "HireSenseセッション完了！",
        "performance_analytics": "HireSenseパフォーマンス分析",
        "ai_report": "HireSense AIレポート",
        "generate_report": "HireSenseレポートを生成",
        "view_report": "HireSenseレポートを表示",
        "full_transcript": "完全なトランスクリプト",
        "start_new_session": "新しいHireSenseセッションを開始",
        "question_bank": "質問バンク",
        "interview": "面接",
        "live_status": "ライブステータス",
        "emotional_state": "感情状態",
        "ai_mode": "AIモード",
        "session_stats": "セッション統計",
        "duration": "時間",
        "exchanges": "やり取り",
        "confident": "自信あり",
        "stressed": "ストレス",
        "neutral": "中立",
        "supportive_mode": "サポートモード",
        "challenge_mode": "チャレンジモード",
        "balanced_mode": "バランスモード",
        "speak_your_answer": "回答を話す",
        "use_this_answer": "この回答を使用",
        "select_language": "言語を選択",
        "language": "言語"
    },
    "hi": {
        "app_title": "HireSense AI",
        "app_subtitle": "बुद्धिमान साक्षात्कार मंच",
        "setup_session": "अपना HireSense सत्र सेट करें",
        "select_interview_type": "साक्षात्कार प्रकार चुनें",
        "upload_resume": "अपना रिज्यूमे अपलोड करें",
        "job_description": "नौकरी विवरण",
        "session_settings": "सत्र सेटिंग्स",
        "num_questions": "प्रश्नों की संख्या",
        "enable_voice": "आवाज सक्षम करें (TTS)",
        "enable_webcam": "वेबकैम सक्षम करें",
        "enable_voice_input": "वॉइस इनपुट सक्षम करें",
        "start_session": "HireSense सत्र शुरू करें",
        "your_response": "आपका उत्तर",
        "submit_answer": "उत्तर सबमिट करें",
        "skip_question": "प्रश्न छोड़ें",
        "end_session": "सत्र समाप्त करें",
        "session_complete": "HireSense सत्र पूर्ण!",
        "performance_analytics": "HireSense प्रदर्शन विश्लेषण",
        "ai_report": "HireSense AI रिपोर्ट",
        "generate_report": "HireSense रिपोर्ट जनरेट करें",
        "view_report": "HireSense रिपोर्ट देखें",
        "full_transcript": "पूर्ण प्रतिलेख",
        "start_new_session": "नया HireSense सत्र शुरू करें",
        "question_bank": "प्रश्न बैंक",
        "interview": "साक्षात्कार",
        "live_status": "लाइव स्थिति",
        "emotional_state": "भावनात्मक स्थिति",
        "ai_mode": "AI मोड",
        "session_stats": "सत्र आंकड़े",
        "duration": "अवधि",
        "exchanges": "आदान-प्रदान",
        "confident": "आत्मविश्वासी",
        "stressed": "तनावग्रस्त",
        "neutral": "तटस्थ",
        "supportive_mode": "सहायक मोड",
        "challenge_mode": "चुनौती मोड",
        "balanced_mode": "संतुलित मोड",
        "speak_your_answer": "अपना उत्तर बोलें",
        "use_this_answer": "इस उत्तर का उपयोग करें",
        "select_language": "भाषा चुनें",
        "language": "भाषा"
    },
    "ur": {
        "app_title": "HireSense AI",
        "app_subtitle": "ذہین انٹرویو پلیٹ فارم",
        "setup_session": "اپنا HireSense سیشن سیٹ اپ کریں",
        "select_interview_type": "انٹرویو کی قسم منتخب کریں",
        "upload_resume": "اپنا ریزیومی اپ لوڈ کریں",
        "job_description": "نوکری کی تفصیل",
        "session_settings": "سیشن کی ترتیبات",
        "num_questions": "سوالات کی تعداد",
        "enable_voice": "آواز فعال کریں (TTS)",
        "enable_webcam": "ویب کیم فعال کریں",
        "enable_voice_input": "آواز ان پٹ فعال کریں",
        "start_session": "HireSense سیشن شروع کریں",
        "your_response": "آپ کا جواب",
        "submit_answer": "جواب جمع کرائیں",
        "skip_question": "سوال چھوڑیں",
        "end_session": "سیشن ختم کریں",
        "session_complete": "HireSense سیشن مکمل!",
        "performance_analytics": "HireSense کارکردگی کا تجزیہ",
        "ai_report": "HireSense AI رپورٹ",
        "generate_report": "HireSense رپورٹ بنائیں",
        "view_report": "HireSense رپورٹ دیکھیں",
        "full_transcript": "مکمل ٹرانسکرپٹ",
        "start_new_session": "نیا HireSense سیشن شروع کریں",
        "question_bank": "سوالات کا ذخیرہ",
        "interview": "انٹرویو",
        "live_status": "لائیو سٹیٹس",
        "emotional_state": "جذباتی کیفیت",
        "ai_mode": "AI موڈ",
        "session_stats": "سیشن کے اعداد و شمار",
        "duration": "دورانیہ",
        "exchanges": "تبادلے",
        "confident": "پراعتماد",
        "stressed": "تناؤ میں",
        "neutral": "غیر جانبدار",
        "supportive_mode": "معاون موڈ",
        "challenge_mode": "چیلنج موڈ",
        "balanced_mode": "متوازن موڈ",
        "speak_your_answer": "اپنا جواب بولیں",
        "use_this_answer": "یہ جواب استعمال کریں",
        "select_language": "زبان منتخب کریں",
        "language": "زبان"
    }
}

# Add remaining languages with English as fallback
for lang_code in SUPPORTED_LANGUAGES:
    if lang_code not in UI_TRANSLATIONS:
        UI_TRANSLATIONS[lang_code] = UI_TRANSLATIONS["en"].copy()


# ============================================================================
# Language Helper Functions
# ============================================================================

def get_language_list() -> List[Dict]:
    """Get list of supported languages for display."""
    return [
        {
            "code": code,
            "name": info["name"],
            "native_name": info["native_name"],
            "flag": info["flag"],
            "display": f"{info['flag']} {info['native_name']} ({info['name']})"
        }
        for code, info in SUPPORTED_LANGUAGES.items()
    ]


def get_language_info(lang_code: str) -> Dict:
    """Get information about a specific language."""
    return SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES["en"])


def get_ui_text(key: str, lang_code: str = "en") -> str:
    """Get translated UI text for a given key."""
    translations = UI_TRANSLATIONS.get(lang_code, UI_TRANSLATIONS["en"])
    return translations.get(key, UI_TRANSLATIONS["en"].get(key, key))


def get_tts_language(lang_code: str) -> str:
    """Get TTS language code for browser speech synthesis."""
    lang_info = get_language_info(lang_code)
    return lang_info.get("tts_lang", "en-US")


def get_speech_recognition_language(lang_code: str) -> str:
    """Get speech recognition language code."""
    lang_info = get_language_info(lang_code)
    return lang_info.get("speech_lang", "en-US")


def get_speech_recognition_code(lang_code: str) -> str:
    """Alias for get_speech_recognition_language for backward compatibility."""
    return get_speech_recognition_language(lang_code)


def get_interview_language_prompt(lang_code: str) -> str:
    """Get language instruction for the AI interviewer."""
    lang_info = get_language_info(lang_code)
    lang_name = lang_info["name"]
    
    if lang_code == "en":
        return ""
    
    return f"""
IMPORTANT: Conduct this entire interview in {lang_name}. 
- Ask all questions in {lang_name}
- Respond to answers in {lang_name}
- Provide feedback in {lang_name}
- Generate the final report in {lang_name}
- Be culturally aware and appropriate for {lang_name}-speaking candidates
"""


def get_language_specific_tts_html(text: str, lang_code: str, speed: float = 1.1) -> str:
    """Generate TTS HTML with language-specific voice."""
    tts_lang = get_tts_language(lang_code)
    clean_text = text.replace('`', '').replace('"', "'").replace('\n', ' ').replace('\\', '').replace("'", "\\'")[:500]
    
    return f"""
    <div id="tts-container">
        <script>
        (function() {{
            function speakNow() {{
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    const utterance = new SpeechSynthesisUtterance('{clean_text}');
                    utterance.rate = {speed};
                    utterance.pitch = 1.0;
                    utterance.volume = 1.0;
                    utterance.lang = '{tts_lang}';
                    
                    const voices = window.speechSynthesis.getVoices();
                    if (voices.length > 0) {{
                        // Try to find a voice matching the language
                        const langPrefix = '{tts_lang}'.split('-')[0];
                        const preferredVoice = voices.find(v => v.lang === '{tts_lang}')
                            || voices.find(v => v.lang.startsWith(langPrefix))
                            || voices.find(v => v.lang.startsWith('en'))
                            || voices[0];
                        if (preferredVoice) utterance.voice = preferredVoice;
                    }}
                    window.speechSynthesis.speak(utterance);
                }}
            }}
            if (window.speechSynthesis.getVoices().length > 0) speakNow();
            else window.speechSynthesis.onvoiceschanged = speakNow;
        }})();
        </script>
    </div>
    """


def get_voice_input_html_with_language(session_key: str, lang_code: str) -> str:
    """Generate voice input HTML with language-specific speech recognition."""
    speech_lang = get_speech_recognition_language(lang_code)
    lang_info = get_language_info(lang_code)
    
    return f'''
    <script>
    // Set speech recognition language
    if (window.recognition) {{
        window.recognition.lang = '{speech_lang}';
    }}
    // Store language preference
    localStorage.setItem('hiresense_speech_lang', '{speech_lang}');
    </script>
    '''


# ============================================================================
# Language Selector Component
# ============================================================================

def render_language_selector_html() -> str:
    """Generate HTML for language selector dropdown."""
    options_html = ""
    for code, info in SUPPORTED_LANGUAGES.items():
        options_html += f'<option value="{code}">{info["flag"]} {info["native_name"]}</option>\n'
    
    return f'''
    <div style="display: inline-block; margin-right: 10px;">
        <select id="language-selector" onchange="changeLanguage(this.value)" 
                style="padding: 8px 12px; border-radius: 8px; border: 1px solid #ddd; 
                       font-size: 14px; cursor: pointer; background: white;">
            {options_html}
        </select>
    </div>
    <script>
    function changeLanguage(langCode) {{
        localStorage.setItem('hiresense_language', langCode);
        // Notify Streamlit of language change
        window.parent.postMessage({{
            type: 'streamlit:setComponentValue',
            value: {{ language: langCode }}
        }}, '*');
    }}
    
    // Load saved language preference
    (function() {{
        const savedLang = localStorage.getItem('hiresense_language') || 'en';
        const selector = document.getElementById('language-selector');
        if (selector) selector.value = savedLang;
    }})();
    </script>
    '''
