from __future__ import annotations

import re

import frappe
from frappe import _

ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
AR_TO_LATIN = {
    "ا":"a","أ":"a","إ":"i","آ":"aa","ب":"b","ت":"t","ث":"th","ج":"j","ح":"h","خ":"kh",
    "د":"d","ذ":"dh","ر":"r","ز":"z","س":"s","ش":"sh","ص":"s","ض":"d","ط":"t","ظ":"z",
    "ع":"a","غ":"gh","ف":"f","ق":"q","ك":"k","ل":"l","م":"m","ن":"n","ه":"h","ة":"a",
    "و":"w","ؤ":"u","ي":"y","ى":"a","ئ":"e","ء":"","َ":"","ً":"","ُ":"","ٌ":"","ِ":"","ٍ":"","ْ":"","ّ":"",
}
LATIN_TOKENS = [("kh","خ"),("gh","غ"),("sh","ش"),("th","ث"),("dh","ذ"),("aa","ا"),("ch","تش"),
                ("a","ا"),("b","ب"),("t","ت"),("j","ج"),("h","ه"),("d","د"),("r","ر"),("z","ز"),
                ("s","س"),("f","ف"),("q","ق"),("k","ك"),("l","ل"),("m","م"),("n","ن"),("w","و"),
                ("o","و"),("u","و"),("y","ي"),("i","ي"),("e","ي"),("g","ج")]


def arabic_to_english(value: str) -> str:
    words = ["".join(AR_TO_LATIN.get(char, char) for char in word) for word in (value or "").split()]
    return " ".join(word[:1].upper() + word[1:] for word in words if word)


def english_to_arabic(value: str) -> str:
    result = []
    for word in (value or "").lower().split():
        output, index = "", 0
        while index < len(word):
            matched = False
            for token, arabic in LATIN_TOKENS:
                if word.startswith(token, index):
                    output += arabic; index += len(token); matched = True; break
            if not matched:
                output += word[index]; index += 1
        result.append(output)
    return " ".join(result)


def apply_bilingual_name(doc, method=None):
    arabic_parts = [(doc.get(field) or "").strip() for field in (
        "custom_first_name_ar", "custom_middle_name_ar", "custom_last_name_ar"
    )]
    if any(arabic_parts):
        doc.custom_employee_name_ar = " ".join(part for part in arabic_parts if part)
    doc.custom_employee_name_en = (doc.employee_name or "").strip()


@frappe.whitelist()
def suggest_name(value: str, target_language: str):
    if not value or target_language not in {"Arabic", "English"}:
        frappe.throw(_("Enter a name and select a valid target language."))
    return english_to_arabic(value) if target_language == "Arabic" else arabic_to_english(value)
