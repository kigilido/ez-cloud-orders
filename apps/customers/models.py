from datetime import date

from django.db import models


class Customer(models.Model):
    family_number = models.CharField(max_length=20, unique=True)
    medicaid_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    address = models.TextField()
    city_state_zip = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20, db_index=True)
    valid_until = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.phone_number})"

    @property
    def is_eligible(self) -> bool:
        return self.valid_until >= date.today()
