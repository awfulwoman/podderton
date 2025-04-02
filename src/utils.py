import os 
import pprint

def define_string_tokens(entry):
    """Given a feed, generate all possible string tokens."""

    parsed_date = entry.get("published_parsed", None)

    yyyy = parsed_date.tm_year if parsed_date else None
    mmmm = parsed_date.tm_mon if parsed_date else None
    dddd = parsed_date.tm_mday if parsed_date else None
    title = entry.get("title", None)
    description = entry.get("description", None)
    episode = entry.get("episode", None)
    season = entry.get("season", None)

    return {
        "yyyy": yyyy,
        "mmmm": mmmm,
        "dddd": dddd,
        "title": title,
        "description": description,
        "episode": episode,
        "season": season,
        "title": title,
        "description": description,
        "episode": episode,
        "season": season,
    }

def replace_string_tokens(string, tokens):
    """Replace string tokens with their corresponding values."""
    for key, value in tokens.items():
        string = string.replace(f"{key}", value)
    return string
