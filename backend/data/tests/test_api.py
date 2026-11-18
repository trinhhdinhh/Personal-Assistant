import pytest
from django.test import Client


@pytest.mark.django_db
def test_report_endpoint_returns_json():
    response = Client().get("/api/report")
    assert response.status_code == 200
    assert response.json() is not None

