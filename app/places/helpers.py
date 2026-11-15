def validate_location(
    address: str | None, latitude: float | None, longitude: float | None
) -> None:
    if (latitude is None) != (longitude is None):
        raise ValueError("latitude and longitude must be provided together")
    if address is None and latitude is None:
        raise ValueError("provide an address, coordinates, or both")
