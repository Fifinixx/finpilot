"""Typed field parsing for CSV rows. Each method returns the parsed value, or
None after recording an error, so all problems in a row are reported at once."""

import datetime as dt
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class RowParser:
    def __init__(self, raw: dict[str, str]):
        self.raw = {k: (v or "").strip() for k, v in raw.items() if k is not None}
        self.errors: list[dict[str, str]] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, field: str, message: str) -> None:
        self.errors.append({"field": field, "message": message})

    def _value(self, col: str, required: bool) -> str | None:
        value = self.raw.get(col, "")
        if value == "":
            if required:
                self.error(col, "is required")
            return None
        return value

    def text(self, col, max_length, required=True):
        value = self._value(col, required)
        if value is None:
            return None if required else ""
        if len(value) > max_length:
            self.error(col, f"must be at most {max_length} characters")
            return None
        return value

    def email(self, col):
        value = self.text(col, 254)
        if value is None:
            return None
        try:
            validate_email(value)
        except ValidationError:
            self.error(col, f"'{value}' is not a valid email address")
            return None
        return value.lower()

    def enum(self, col, choices):
        value = self._value(col, True)
        if value is None:
            return None
        allowed = [c for c, _ in choices.choices]
        if value not in allowed:
            self.error(col, f"'{value}' is not one of {', '.join(allowed)}")
            return None
        return value

    def date(self, col):
        value = self._value(col, True)
        if value is None:
            return None
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            self.error(col, f"'{value}' is not a valid date (expected YYYY-MM-DD)")
            return None

    def decimal(self, col, max_digits, decimal_places, min_value=None, gt=None):
        value = self._value(col, True)
        if value is None:
            return None
        try:
            number = Decimal(value)
        except InvalidOperation:
            self.error(col, f"'{value}' is not a number")
            return None
        if not number.is_finite():
            self.error(col, f"'{value}' is not a finite number")
            return None
        sign, digits, exponent = number.as_tuple()
        places = max(0, -exponent)
        if places > decimal_places:
            # Reject instead of silently rounding money/quantities.
            self.error(col, f"'{value}' has more than {decimal_places} decimal places")
            return None
        if len(digits) - places > max_digits - decimal_places:
            self.error(col, f"'{value}' is too large")
            return None
        if gt is not None and number <= gt:
            self.error(col, f"must be greater than {gt}")
            return None
        if min_value is not None and number < min_value:
            self.error(col, "must not be negative" if min_value == 0 else f"must be at least {min_value}")
            return None
        return number

    def integer(self, col, min_value, max_value):
        value = self._value(col, True)
        if value is None:
            return None
        try:
            number = int(value)
        except ValueError:
            self.error(col, f"'{value}' is not a whole number")
            return None
        if not min_value <= number <= max_value:
            self.error(col, f"must be between {min_value} and {max_value}")
            return None
        return number

    def ref(self, col, valid_ids: set[str], label: str):
        """Foreign-key check against a preloaded set of IDs (no per-row query)."""
        value = self._value(col, True)
        if value is None:
            return None
        if value not in valid_ids:
            self.error(col, f"{label} '{value}' does not exist")
            return None
        return value
