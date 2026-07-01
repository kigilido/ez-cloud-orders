from apps.core.utils import normalize_phone
from apps.customers.models import Customer


def check_eligibility(phone_number: str) -> dict:
    """
    Customer is eligible if their phone exists in the Spruce list
    and valid_until >= today.
    """
    normalized = normalize_phone(phone_number)
    if not normalized:
        return {"found": False, "customer": None, "is_eligible": False}

    customer = Customer.objects.filter(phone_number__icontains=normalized).first()
    if customer is None:
        return {"found": False, "customer": None, "is_eligible": False}

    return {
        "found": True,
        "customer": customer,
        "is_eligible": customer.is_eligible,
    }
