"""Speech hints without changing saved titles, IDs or business tool results."""

import re


SPEECH_GUIDANCE = (
    "Speak in natural sentences in the user's current language. When summarizing a task, "
    "prefer its speech_title and briefly explain technical wording in that language. "
    "Do not read formatting separators as 'slash', 'dot', 'asterisk' or their translations. "
    "Never spell a path, URL or identifier unless the user asks; preserve exact names and numbers "
    "when they matter. Do not insert English fillers into Mandarin or Cantonese. "
    "When saying HKD in Mandarin or Cantonese use a single decimal amount followed by 港元. "
    "For a verified fare use its fare_amount.spoken_zh exactly. Keep cent digits in order, including a leading zero. "
    "For weather anywhere, delegate weather_query with the actual city and the spoken language. "
    "For a general weather or rain question use today in the destination. Speak its current conditions, "
    "daily range and sourced precipitation outlook as a short natural answer using its summary. "
)


def speech_result(value):
    """Only the model-facing voice copy gains a punctuation-free title hint."""
    if isinstance(value, list):
        return [speech_result(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: speech_result(item) for key, item in value.items()}
    title = value.get("title")
    if isinstance(title, str):
        # Spaced separators are presentation punctuation; dates, fractions,
        # URLs and compact file paths must keep their original meaning.
        result["speech_title"] = re.sub(r"\s+[·•/]\s+", ", ", title)
    return result
