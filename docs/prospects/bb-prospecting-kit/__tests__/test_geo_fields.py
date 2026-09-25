"""Tests for geo_fields.city_from_address — the location parse shared by the pipeline.

A wrong city is worse than a missing one: it decides whether a lead is in the service area
at all, so the parser returns "" rather than guessing when the string is not in US address
order.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geo_fields import city_from_address, location_fields  # noqa: E402


def test_reads_the_city_before_the_state_tail():
    assert city_from_address("2317 Toonigh Rd, Canton, GA 30115") == "Canton"


def test_ignores_a_suite_between_street_and_city():
    assert city_from_address("225 Reformation Pkwy Ste 200, Canton, GA 30115") == "Canton"
    assert city_from_address("110 Samaritan Dr 212 Office #2, Cumming, GA 30040") == "Cumming"


def test_handles_a_zip_plus_four():
    assert city_from_address("258 Coddington Ct, Suwanee, GA 30024-1234") == "Suwanee"


def test_handles_city_and_state_without_a_street_or_zip():
    assert city_from_address("Canton, GA") == "Canton"
    assert city_from_address("Canton, GA 30114") == "Canton"


def test_state_tail_is_case_insensitive():
    assert city_from_address("2317 Toonigh Rd, Canton, ga 30115") == "Canton"


def test_returns_empty_rather_than_guessing_a_street_fragment():
    """No state tail means this is not a parseable US address; do not invent a city."""
    assert city_from_address("2317 Toonigh Rd") == ""
    assert city_from_address("Suite 200") == ""
    assert city_from_address("") == ""
    assert city_from_address(None) == ""


def test_a_business_in_another_town_is_reported_as_such():
    """The case this exists for: a lead ranking in one city's search but located elsewhere."""
    assert city_from_address("2475 Northwinds Pkwy Suite 200, Alpharetta, GA 30009") == "Alpharetta"


def test_location_fields_carries_address_and_website_through():
    got = location_fields("2317 Toonigh Rd, Canton, GA 30115", "https://frittsheatingandair.com/")
    assert got == {"city": "Canton", "address": "2317 Toonigh Rd, Canton, GA 30115",
                   "website": "https://frittsheatingandair.com/"}


def test_location_fields_leaves_values_empty_when_unavailable():
    assert location_fields("", "") == {"city": "", "address": "", "website": ""}
