"""Tests for request parser validation logic."""

from agents.request_parser_agent import validate_parsed_fields, format_missing_fields_message


def test_all_fields_present():
    parsed = {"origin": "Delhi", "destination": "Mumbai", "venue": "Wankhede Stadium", "event_date": "2026-08-10", "travelers": 2}
    assert validate_parsed_fields(parsed) == []


def test_missing_origin_venue_event_date():
    parsed = {"origin": "", "destination": "Mumbai", "venue": "", "event_date": "", "travelers": None}
    missing = validate_parsed_fields(parsed)
    assert missing == ["origin", "venue", "event_date"]
    assert format_missing_fields_message(missing) == "Please provide the following information: origin, venue, event_date."


def test_parser_extracts_from_junk():
    parsed = {"origin": "Chennai", "destination": "Bangalore", "venue": "Chinnaswamy Stadium", "event_date": "2026-09-04", "travelers": None}
    assert validate_parsed_fields(parsed) == []


def test_empty_dict_all_missing():
    missing = validate_parsed_fields({})
    assert missing == ["origin", "destination", "venue", "event_date"]
    assert format_missing_fields_message(missing) == "Please provide the following information: origin, destination, venue, event_date."


def test_whitespace_only_field_detected():
    parsed = {"origin": "Delhi", "destination": "Mumbai", "venue": "   ", "event_date": "2026-08-10"}
    assert validate_parsed_fields(parsed) == ["venue"]


def test_single_missing_field_message():
    assert format_missing_fields_message(["origin"]) == "Please provide the origin."


def test_two_missing_fields_message():
    assert format_missing_fields_message(["destination", "venue"]) == "Please provide the destination and venue."


def test_structured_request_passes():
    parsed = {"origin": "MIA", "destination": "EWR", "venue": "Prudential Center", "event_date": "2026-07-15", "travelers": 1}
    assert validate_parsed_fields(parsed) == []


def test_none_values_detected():
    parsed = {"origin": None, "destination": None, "venue": None, "event_date": None}
    missing = validate_parsed_fields(parsed)
    assert missing == ["origin", "destination", "venue", "event_date"]


def test_empty_string_values_detected():
    parsed = {"origin": "", "destination": "", "venue": "", "event_date": ""}
    missing = validate_parsed_fields(parsed)
    assert missing == ["origin", "destination", "venue", "event_date"]


def test_travelers_not_required():
    parsed = {"origin": "Delhi", "destination": "Mumbai", "venue": "Concert", "event_date": "2026-08-10"}
    assert validate_parsed_fields(parsed) == []
