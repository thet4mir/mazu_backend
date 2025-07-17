import os
import re
from openai import OpenAI
import unicodedata
from dotenv import load_dotenv


load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

def sanitize_mongolian(text: str, keep_punctuation: bool = True) -> str:
    """
    Strictly removes `, " - ²` while preserving:
    - Mongolian Cyrillic (including Өө, Үү)
    - Numbers (0-9)
    - Spaces
    - Optional basic punctuation (.?!) if `keep_punctuation=True`

    Returns: (cleaned_text, needs_further_processing)
    """
    # Define allowed characters (Unicode ranges)
    mongolian_cyrillic = (
        r"\u0410-\u044F"  # Basic Cyrillic
        r"\u0401\u0451"   # Ёё
        r"\u04AE\u04AF"   # Үү
        r"\u04E8\u04E9"   # Өө
    )
    allowed_chars = f"{mongolian_cyrillic}0-9\\s"

    # Add allowed punctuation (.,?!) only if enabled
    if keep_punctuation:
        allowed_chars += r".?!"

    # Step 1: Remove explicitly unwanted chars (`, " - ²`)
    # Note: `²` is Unicode \u00B2
    cleaned = re.sub(r'[,"\-\u00B2!]', ' ', text)

    # Step 2: Remove any other non-allowed characters
    cleaned = re.sub(f"[^{allowed_chars}]", ' ', cleaned)

    # Normalize whitespace (replace multiple spaces with one)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned


def _check_mongolian_quality(cleaned: str, original: str) -> bool:
    """Heuristic check for Mongolian text integrity"""
    # Check if we lost more than 30% of non-space characters
    orig_len = len([c for c in original if not c.isspace()])
    clean_len = len([c for c in cleaned if not c.isspace()])
    
    if clean_len / orig_len < 0.7:
        return True
    
    # Check for critical Mongolian words removal
    mongolian_keywords = ["байна", "юм", "бол", "биш"]  # Add more
    return not any(word in cleaned for word in mongolian_keywords)


def mongolian_tts_pipeline(text: str) -> str:
    """Complete processing pipeline for Mongolian TTS"""
    # First pass - preserve punctuation
    cleaned, needs_processing = sanitize_mongolian(text, keep_punctuation=True)
    
    if not needs_processing:
        return cleaned
    
    # Second pass - more aggressive if needed
    cleaned, _ = sanitize_mongolian(text, keep_punctuation=False)
    
    # LLM fallback for meaning reconstruction (if available)
    return _mongolian_llm_correction(cleaned)
    

def _mongolian_llm_correction(text: str) -> str:
    """Use LLM to reconstruct Mongolian text"""
    # Example prompt for Mongolian LLM
    prompt = f"""
    Дараах текстийг хэт их өөрчлөхгүй, утга санааг алдалгүй дахин бичиж өгнө үү.
    Зөвхөн кирилл үсэг, тоо, цэг таслал ашиглана уу.
    
    Оролт: {text}
    Гаралт:
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )

    print(response.choices[0].message.content)
    # Call your Mongolian-capable LLM here
    # return llm.generate(prompt)
    return response.choices[0].message.content


def number_to_mongolian(n):
    ones = ["", "нэг", "хоёр", "гурав", "дөрөв", "тав", "зургаа", "долоо", "найм", "ес"]
    tens_root = ["", "арав", "хорь", "гуч", "дөч", "тавь", "жар", "дал", "ная", "ер"]
    tens_compound = ["", "арван", "хорин", "гучин", "дөчин", "тавин", "жаран", "далан", "наян", "ерэн"]
    hundreds = ["", "нэг зуу", "хоёр зуу", "гурав зуу", "дөрөв зуу", "тав зуу",
                "зургаа зуу", "долоон зуу", "найман зуу", "есөн зуу"]

    def convert_chunk(num):
        h = num // 100
        t = (num % 100) // 10
        o = num % 10
        parts = []

        if h > 0:
            parts.append(hundreds[h])

        if t == 0 and o > 0:
            parts.append(ones[o])
        elif t > 0 and o == 0:
            parts.append(tens_root[t])
        elif t > 0 and o > 0:
            parts.append(tens_compound[t] + " " + ones[o])
        elif num == 0 and not parts:
            parts.append("тэг")

        return " ".join(parts)

    if n == 0:
        return "тэг"

    parts = []
    billions = n // 1_000_000_000
    millions = (n // 1_000_000) % 1_000
    thousands = (n // 1_000) % 1_000
    remainder = n % 1_000

    if billions:
        parts.append(convert_chunk(billions) + " тэрбум")
    if millions:
        parts.append(convert_chunk(millions) + " сая")
    if thousands:
        parts.append(convert_chunk(thousands) + " мянга")
    if remainder:
        parts.append(convert_chunk(remainder))

    return " ".join(parts)

# ✅ Replace all numbers in string with their Mongolian text equivalents
def replace_numbers_with_mongolian(text):
    def replacer(match):
        num = int(match.group())
        return number_to_mongolian(num)
    
    return re.sub(r'\b\d+\b', replacer, text)