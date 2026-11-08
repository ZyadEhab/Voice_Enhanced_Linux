# tests/test_nlp.py
import pytest
from nlp.understanding import understand

def test_english_file_commands():
    # اختبار أمر عرض الملفات بالإنجليزية
    result = understand("Show my files", "en")
    assert result["intent"] == "LIST_FILES"
    assert result["confidence"] > 0.0

def test_arabic_file_commands():
    # اختبار أمر عرض الملفات بالعربية
    result = understand("اعرض ملفاتي", "ar")
    assert result["intent"] == "LIST_FILES"
    assert result["confidence"] > 0.0

def test_application_commands():
    # اختبار فتح التطبيقات
    result = understand("Open firefox", "en")
    assert result["intent"] == "OPEN_APPLICATION"
    assert result["params"].get("app") == "firefox"
    assert result["needs_confirmation"] == False

    # اختبار إغلاق التطبيق (يجب أن يتطلب تأكيداً)
    result_close = understand("Close firefox", "en")
    assert result_close["intent"] == "CLOSE_APPLICATION"
    assert result_close["needs_confirmation"] == True

def test_multiple_commands_guard():
    # اختبار حارس الأوامر المتعددة (يجب أن يرفض جمل تحتوي على أمرين معاً)
    result = understand("open firefox and delete report", "en")
    assert result["intent"] == "UNKNOWN"
    assert result["method"] == "guard_rejected"

def test_empty_input():
    # اختبار المدخلات الفارغة
    result = understand("", "en")
    assert result["intent"] == "UNKNOWN"
    assert result["confidence"] == 0.0