import sys
import time

sys.path.insert(0, "src/")
import utils


# --- define_string_tokens ---

def test_define_string_tokens_date():
    entry = {"published_parsed": time.strptime("2024-06-15", "%Y-%m-%d")}
    tokens = utils.define_string_tokens(entry)
    assert tokens["yyyy"] == 2024
    assert tokens["mmmm"] == 6
    assert tokens["dddd"] == 15


def test_define_string_tokens_content():
    entry = {
        "title": "My Episode",
        "description": "A great episode",
        "episode": "3",
        "season": "2",
    }
    tokens = utils.define_string_tokens(entry)
    assert tokens["title"] == "My Episode"
    assert tokens["description"] == "A great episode"
    assert tokens["episode"] == "3"
    assert tokens["season"] == "2"


def test_define_string_tokens_missing_fields():
    entry = {"title": "Minimal"}
    # Should not raise
    tokens = utils.define_string_tokens(entry)
    assert tokens["title"] == "Minimal"
    assert tokens["yyyy"] is None
    assert tokens["mmmm"] is None
    assert tokens["dddd"] is None
    assert tokens["episode"] is None
    assert tokens["season"] is None


# --- replace_string_tokens ---

def test_replace_string_tokens_basic():
    result = utils.replace_string_tokens(
        "{yyyy}-{mmmm}-{dddd} {title}.ext",
        {"yyyy": "2024", "mmmm": "06", "dddd": "15", "title": "My Episode"},
    )
    assert result == "2024-06-15 My Episode.ext"


def test_replace_string_tokens_null_values():
    result = utils.replace_string_tokens(
        "{title} - {episode}.ext",
        {"title": "Good Ep", "episode": None},
    )
    # None should become empty string, not "None"
    assert result == "Good Ep - .ext"
    assert "None" not in result


def test_replace_string_tokens_no_matching_tokens():
    result = utils.replace_string_tokens(
        "plain-filename.ext",
        {"title": "Ignored", "yyyy": "2024"},
    )
    assert result == "plain-filename.ext"


def test_replace_string_tokens_patterns():
    # Default {title}.ext pattern
    result = utils.replace_string_tokens("{title}.ext", {"title": "My Episode"})
    assert result == "My Episode.ext"

    # {yyyy}-{mmmm}-{dddd} separate tokens (actual working pattern)
    result = utils.replace_string_tokens(
        "{yyyy}-{mmmm}-{dddd}.ext",
        {"yyyy": 2024, "mmmm": 6, "dddd": 15},
    )
    assert result == "2024-6-15.ext"

    # {yyyy-mm-dd} as a single token - no matching key, left unchanged
    result = utils.replace_string_tokens(
        "{yyyy-mm-dd}.ext",
        {"yyyy": 2024, "mmmm": 6, "dddd": 15},
    )
    assert result == "{yyyy-mm-dd}.ext"

    # {episode} - {title}.ext
    result = utils.replace_string_tokens(
        "{episode} - {title}.ext",
        {"episode": "3", "title": "Finale"},
    )
    assert result == "3 - Finale.ext"
