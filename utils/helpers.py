def safe_float(value):

    try:
        return float(value)
    except:
        return 0


def safe_int(value):

    try:
        return int(value)
    except:
        return 0


def normalize_text(text):

    if not text:
        return ""

    return text.strip().lower()