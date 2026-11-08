import re
from sentence_transformers import SentenceTransformer, util
from nlp.intents import SUPPORTED_INTENTS, ALLOWED_APPS, ALLOWED_RESOURCES

# تحميل نموذج المطابقة الدلالية مرة واحدة عند بدء التشغيل
# نموذج paraphrase-multilingual-MiniLM-L12-v2 يدعم العربية والإنجليزية بكفاءة
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_model = None

def get_model():
    global _model
    if _model is None:
        try:
            _model = SentenceTransformer(MODEL_NAME)
        except Exception as e:
            print(f"Warning: Could not load transformer model: {e}")
            _model = None
    return _model

def normalize_text(text: str) -> str:
    """معالجة وتطبيع النص: توحيد الحروف، إزالة التشكيل وعلامات الترقيم"""
    if not text:
        return ""
    text = text.lower().strip()
    # إزالة التشكيل العربي
    text = re.sub(r'[\u064b-\u0652]', '', text)
    # توحيد أشكال الهمزات والألفات (أ إ آ -> ا)
    text = re.sub(r'[أإآ]', 'ا', text)
    # توحيد التهاء المربوطة والهاء (ة -> ه) و(ى -> ي)
    text = text.replace('ة', 'ه').replace('ى', 'ي')
    # إزالة علامات الترقيم الزائدة
    text = re.sub(r'[^\w\s]', '', text)
    return text

def check_multiple_commands(text: str) -> bool:
    """حارس الأوامر المتعددة: رفض الجمل التي تحتوي على أكثر من أمر بربط الواو أو ثم"""
    conjunctions = [" و ", " ثم ", " and ", " then "]
    for conj in conjunctions:
        if conj in text:
            return True
    return False

def keyword_fallback(text: str):
    """الوضع الاحتياطي للكلمات المفتاحية في حال تعذر نموذج الذكاء الاصطناعي"""
    normalized = normalize_text(text)
    for intent, data in SUPPORTED_INTENTS.items():
        for lang_phrases in data.values():
            for phrase in lang_phrases:
                if normalize_text(phrase) in normalized:
                    return intent, 0.75  # الثقة في الكلمات المفتاحية محددة بحد أقصى
    return "UNKNOWN", 0.0

def extract_parameters(intent: str, text: str):
    """استخراج المعلمات المطلوبة بناءً على النية (مثل اسم الملف أو التطبيق)"""
    params = {}
    missing = []
    text_lower = text.lower()

    if intent in ["CREATE_FILE", "CREATE_FOLDER", "RENAME_FILE", "DELETE_FILE"]:
        # استخراج اسم الملف أو المجلد بعد الكلمات الدلالية
        words = text.split()
        if len(words) > 1:
            params["name"] = words[-1]  # افتراض أن الاسم هو الكلمة الأخيرة كمثال بسيط
        else:
            missing.append("name")

    elif intent == "OPEN_APPLICATION" or intent == "CLOSE_APPLICATION":
        # مطابقة التطبيق مع الأسماء المسموحة
        app_target = None
        for key, val in ALLOWED_APPS.items():
            if key in text_lower:
                app_target = val
                break
        params["app"] = app_target
        if not app_target:
            missing.append("app")

    elif intent == "SHOW_SYSTEM_USAGE":
        resource_target = None
        for key, val in ALLOWED_RESOURCES.items():
            if key in text_lower:
                resource_target = val
                break
        params["resource"] = resource_target or "ram" # افتراضي

    return params, missing

def understand(text: str, language: str = "en") -> dict:
    """الدالة الرئيسية المطلوبة في عقد الواجهات للتحويل من نص إلى Intent منظم"""
    if not text:
        return {
            "text": "",
            "intent": "UNKNOWN",
            "params": {},
            "confidence": 0.0,
            "method": "none",
            "needs_confirmation": False,
            "missing": []
        }

    # 1. فحص الأوامر المتعددة المرفوضة
    if check_multiple_commands(text):
        return {
            "text": text,
            "intent": "UNKNOWN",
            "params": {},
            "confidence": 0.0,
            "method": "guard_rejected",
            "needs_confirmation": False,
            "missing": [],
            "error": "Multiple commands in one sentence are not allowed."
        }

    model = get_model()
    best_intent = "UNKNOWN"
    confidence = 0.0
    method = "keyword"

    # 2. استخدام المطابقة الدلالية إذا كان النموذج متاحاً
    if model is not None:
        try:
            # جمع كل العبارات المتاحة للتدريب
            all_phrases = []
            phrase_to_intent = {}
            for intent, data in SUPPORTED_INTENTS.items():
                for lang, phrases in data.items():
                    for p in phrases:
                        all_phrases.append(p)
                        phrase_to_intent[p] = intent

            # حساب التشابه الدلالي
            text_embedding = model.encode(text, convert_to_tensor=True)
            phrase_embeddings = model.encode(all_phrases, convert_to_tensor=True)
            cos_scores = util.cos_sim(text_embedding, phrase_embeddings)[0]

            best_idx = cos_scores.argmax().item()
            best_score = cos_scores[best_idx].item()

            # عتبة القبول >= 0.55 كما هو محدد في المواصفات
            if best_score >= 0.55:
                best_intent = phrase_to_intent[all_phrases[best_idx]]
                confidence = round(best_score, 2)
                method = "semantic"
        except Exception as e:
            print(f"Semantic matching error: {e}")

    # 3. تفعيل الاحتياطي (Fallback) إذا كانت الثقة ضعيفة أو النموذج غير متاح
    if confidence < 0.55:
        best_intent, confidence = keyword_fallback(text)
        method = "keyword"

    # 4. استخراج المعلمات
    params, missing = extract_parameters(best_intent, text)

    # 5. تحديد هل العملية تتطلب تأكيد (مثل الحذف أو إغلاق تطبيق)
    needs_confirmation = best_intent in ["DELETE_FILE", "CLOSE_APPLICATION"]

    return {
        "text": text,
        "intent": best_intent,
        "params": params,
        "confidence": confidence,
        "method": method,
        "needs_confirmation": needs_confirmation,
        "missing": missing
    }