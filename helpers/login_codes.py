import re


class LoginCodes(object):
    """'Container' for all valid login codes."""

    def __contains__(self, value) -> bool:
        if not isinstance(value, str):
            return False
        return bool(re.fullmatch(r'\d{4,6}', value))

    def __iter__(self):
        yield '000000'
