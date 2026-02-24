def parse_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in ("true", "1", "on", "yes"):
        return True
    if normalized in ("false", "0", "off", "no"):
        return False
    return None
