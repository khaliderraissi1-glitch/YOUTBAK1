from app.utils import format_duration, format_number, normalize_youtube_url

def test_url_normalization():
    assert normalize_youtube_url("https://youtu.be/abcDEF_1234?t=5") == "https://www.youtube.com/watch?v=abcDEF_1234"

def test_formatting():
    assert format_duration(74) == "1m 14s"
    assert format_number(2300000) == "2.3M"
