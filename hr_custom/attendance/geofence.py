from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_METERS = 6371000.0


def get_distance_in_meters(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * asin(sqrt(a))


def validate_coordinates(latitude, longitude):
    latitude, longitude = float(latitude), float(longitude)
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")
    return latitude, longitude

