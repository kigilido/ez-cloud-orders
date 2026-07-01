from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from apps.customers.services import check_eligibility


@require_GET
def search_by_phone(request: HttpRequest) -> JsonResponse:
    phone = request.GET.get("phone", "").strip()
    if not phone:
        return JsonResponse({"error": "phone parameter is required"}, status=400)

    result = check_eligibility(phone)
    customer = result["customer"]
    return JsonResponse(
        {
            "found": result["found"],
            "is_eligible": result["is_eligible"],
            "customer": {
                "id": customer.pk,
                "family_number": customer.family_number,
                "medicaid_id": customer.medicaid_id,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "address": customer.address,
                "city_state_zip": customer.city_state_zip,
                "phone_number": customer.phone_number,
                "valid_until": customer.valid_until.isoformat(),
                "notes": customer.notes,
            }
            if customer
            else None,
        }
    )
