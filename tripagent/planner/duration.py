from typing import Any, Dict

# Estimated visit durations (in minutes) by Google Places (New) place type.
# Grouped from highest to lowest matching priority.
_TYPE_DURATIONS: dict[str, int] = {
    # Museums and Culture
    "museum": 90,
    "art_gallery": 75,
    "cultural_center": 60,
    "library": 45,
    "performing_arts_theater": 120,
    "concert_hall": 120,

    # Nature and Parks
    "national_park": 120,
    "park": 60,
    "botanical_garden": 75,
    "zoo": 120,
    "aquarium": 90,
    "wildlife_park": 90,

    # Tourist Attractions
    "tourist_attraction": 60,
    "amusement_park": 180,
    "theme_park": 180,
    "water_park": 180,
    "observation_deck": 30,
    "monument": 30,
    "sculpture": 20,
    "historic_landmark": 45,

    # Religious Places
    "church": 45,
    "cathedral": 60,
    "mosque": 30,
    "synagogue": 30,
    "hindu_temple": 30,
    "place_of_worship": 30,

    # Food and Drink
    "restaurant": 75,
    "cafe": 45,
    "coffee_shop": 30,
    "bar": 60,
    "food_court": 45,
    "bakery": 20,
    "ice_cream_shop": 20,
    "fast_food_restaurant": 30,
    "meal_delivery": 20,

    # Shopping
    "shopping_mall": 120,
    "market": 60,
    "supermarket": 45,
    "department_store": 60,
    "clothing_store": 45,
    "book_store": 30,
    "gift_shop": 20,

    # Sports and Leisure
    "stadium": 150,
    "sports_complex": 90,
    "gym": 60,
    "spa": 90,
    "casino": 120,
    "movie_theater": 150,
    "bowling_alley": 90,
    "karaoke": 90,

    # Transport (short time)
    "transit_station": 10,
    "bus_station": 10,
    "train_station": 15,
    "airport": 60,
    "ferry_terminal": 20,

    # Accommodation (reference)
    "hotel": 10,
    "lodging": 10,

    # Other points of interest
    "beach": 120,
    "viewpoint": 30,
    "lighthouse": 20,
    "castle": 90,
    "palace": 90,
    "ruins": 60,
    "cave": 60,
    "waterfall": 45,
}

# Fallback if no known type matches
_DEFAULT_DURATION = 60


def estimate_visit_duration_min(place: Dict[str, Any]) -> int:
    """
    Estimates the visit duration in minutes based on the place types.
    Uses the first match found in _TYPE_DURATIONS (priority order).
    If no type matches, returns 60 minutes.

    MVP Note: replaceable in the future by an AI-based estimation module
    that considers popularity, reviews, and traveler profile.
    """
    types = place.get("types") or []
    for t in types:
        if t in _TYPE_DURATIONS:
            return _TYPE_DURATIONS[t]
    return _DEFAULT_DURATION
