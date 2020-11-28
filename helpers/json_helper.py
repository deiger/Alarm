import json


class JsonEncoder(json.JSONEncoder):
    """Class for JSON encoding."""

    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)

        return json.JSONEncoder.default(self, obj)


def to_json(data: dict) -> bytes:
    """Encode the provided dictionary as JSON."""
    return bytes(json.dumps(data, cls=JsonEncoder), "utf-8")
