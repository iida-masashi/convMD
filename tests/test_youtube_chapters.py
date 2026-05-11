from unittest.mock import patch

from convmd.parsers.sns import youtube


SAMPLE_HTML = '''
{"chapterRenderer":{"title":{"simpleText":"Intro"},"timeRangeStartMillis":0}}
{"chapterRenderer":{"title":{"simpleText":"Main"},"timeRangeStartMillis":60000}}
{"chapterRenderer":{"title":{"simpleText":"Outro"},"timeRangeStartMillis":180000}}
'''


@patch("convmd.parsers.sns.youtube.get_html")
def test_fetch_chapters_from_renderer(mock_get_html):
    mock_get_html.return_value = SAMPLE_HTML
    chapters = youtube.fetch_chapters("dummyVideo1")
    titles = [t for _, t in chapters]
    assert titles == ["Intro", "Main", "Outro"]
    assert chapters[1][0] == 60.0


@patch("convmd.parsers.sns.youtube.get_html")
def test_fetch_chapters_description_fallback(mock_get_html):
    desc = (
        '"shortDescription":"0:00 Intro\\n1:30 Topic\\n10:00 Closing"'
    )
    mock_get_html.return_value = desc
    chapters = youtube.fetch_chapters("dummyVideo2")
    titles = [t for _, t in chapters]
    assert "Intro" in titles
    assert "Topic" in titles


def test_parse_timestamp():
    assert youtube._parse_timestamp("1:30") == 90.0
    assert youtube._parse_timestamp("1:00:00") == 3600.0
    assert youtube._parse_timestamp("garbage") == 0.0
