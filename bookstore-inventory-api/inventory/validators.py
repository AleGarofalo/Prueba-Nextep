"""Reusable inventory field validation."""

import re

from django.core.exceptions import ValidationError


def normalize_isbn(value: str) -> str:
    """Store ISBNs without display separators and with an uppercase check digit."""
    return re.sub(r"[-\s]", "", value).upper()


def validate_isbn(value: str) -> None:
    """Validate an unseparated ISBN-10 or ISBN-13, including its check digit."""
    if re.fullmatch(r"[0-9]{9}[0-9X]", value):
        digits = [10 if character == "X" else int(character) for character in value]
        checksum = sum((10 - index) * digit for index, digit in enumerate(digits))
        if checksum % 11 == 0:
            return
    elif re.fullmatch(r"97[89][0-9]{10}", value):
        checksum = sum(
            int(character) * (1 if index % 2 == 0 else 3)
            for index, character in enumerate(value)
        )
        if checksum % 10 == 0:
            return

    raise ValidationError(
        "Enter a valid ISBN-10 or ISBN-13 without spaces or hyphens "
        "(ISBN-10 may end in X).",
        code="invalid_isbn",
    )
