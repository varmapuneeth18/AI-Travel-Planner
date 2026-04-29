from __future__ import annotations

import os
from typing import Any

import requests


PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join(
    [
        "places.displayName",
        "places.formattedAddress",
        "places.rating",
        "places.userRatingCount",
        "places.googleMapsUri",
        "places.websiteUri",
        "places.priceLevel",
        "places.primaryTypeDisplayName",
        "places.editorialSummary",
    ]
)


def search_places(query: str, page_size: int = 5, included_type: str | None = None) -> list[dict[str, Any]]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return []

    body: dict[str, Any] = {
        "textQuery": query,
        "pageSize": page_size,
    }
    if included_type:
        body["includedType"] = included_type

    try:
        response = requests.post(
            PLACES_SEARCH_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
            json=body,
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
        places = payload.get("places", [])
        normalized: list[dict[str, Any]] = []
        for place in places:
            normalized.append(
                {
                    "name": place.get("displayName", {}).get("text", ""),
                    "address": place.get("formattedAddress", ""),
                    "rating": place.get("rating"),
                    "user_ratings_total": place.get("userRatingCount"),
                    "maps_uri": place.get("googleMapsUri"),
                    "website_uri": place.get("websiteUri"),
                    "price_level": place.get("priceLevel"),
                    "type_label": place.get("primaryTypeDisplayName", {}).get("text", ""),
                    "summary": place.get("editorialSummary", {}).get("text", ""),
                }
            )
        return normalized
    except Exception:
        return []


def google_flights_link(origin: str, destination: str, start_date: str, end_date: str) -> str:
    origin_q = origin.replace(" ", "+")
    destination_q = destination.replace(" ", "+")
    return (
        "https://www.google.com/travel/flights?q="
        f"{origin_q}+to+{destination_q}+{start_date}+return+{end_date}"
    )


def kayak_link(origin: str, destination: str, start_date: str, end_date: str) -> str:
    origin_q = origin.replace(" ", "-")
    destination_q = destination.replace(" ", "-")
    return f"https://www.kayak.com/flights/{origin_q}-{destination_q}/{start_date}/{end_date}"
