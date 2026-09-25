"""Address-derived location fields, shared by the pipeline.

The Maps card gives a business an address and a website; it does NOT give a city as its
own field, and a lead's city is not cosmetic: a business can rank in one town's search
while sitting in another (a Marietta restoration firm ranking in a Canton duct search),
and that changes whether the lead is in the service area at all.

One implementation, because the same parse feeds the candidate CSV, the per-business
capture and the ledger. Three copies is how one business ends up filed under two cities.
"""

import re

# A trailing "GA" or "GA 30115" or "GA 30115-1234" segment marks the state tail. Anything
# else in that position means the string is not in US address order, so we return nothing
# rather than guess a street fragment as the city.
_STATE_TAIL = re.compile(r"^([A-Z]{2})(?:\s+\d{5}(?:-\d{4})?)?$")


def city_from_address(address: str) -> str:
    """City from a Maps address string. Returns '' when it cannot be read.

    Handles the forms Maps actually emits::

        "2317 Toonigh Rd, Canton, GA 30115"              -> "Canton"
        "225 Reformation Pkwy Ste 200, Canton, GA 30115" -> "Canton"
        "Canton, GA 30114"                               -> "Canton"
        "Canton, GA"                                     -> "Canton"
        "2317 Toonigh Rd"                                -> ""   (no state tail)
        ""                                               -> ""
    """
    parts = [p.strip() for p in (address or "").split(",") if p.strip()]
    # Maps sometimes appends the country ("..., Canton, GA 30115, United States")
    if parts and parts[-1].lower() in ("usa", "us", "united states", "united states of america"):
        parts.pop()
    if len(parts) < 2:
        return ""
    if not _STATE_TAIL.match(parts[-1].upper()):
        return ""
    # the city is the segment immediately before the state tail; any suite or unit sits
    # earlier in the string ("... Ste 200, Canton, GA"), so this needs no further logic
    return parts[-2]


def location_fields(address: str, website: str = "") -> dict:
    """The location block every record carries, with values left empty when unavailable."""
    return {"city": city_from_address(address), "address": (address or "").strip(),
            "website": (website or "").strip()}
