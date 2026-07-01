import re


def normalize_phone(phone: str) -> str:
    """Strip non-digit characters from a phone number for consistent lookup."""
    return re.sub(r"\D", "", phone)
