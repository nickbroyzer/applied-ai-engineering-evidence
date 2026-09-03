"""Phase 9-1 §14 — Stripe Customer Portal endpoint (D66)."""
from app import models


def test_customer_portal_200_when_user_has_customer(
    auth_client, picker_user, db_session, mocker,
):
    picker_user.stripe_customer_id = "cus_test_existing"
    db_session.add(picker_user)
    db_session.commit()

    session_mock = mocker.MagicMock()
    session_mock.url = "https://billing.stripe.com/session/test_url"
    portal_create = mocker.patch(
        "app.routers.stripe_billing.stripe.billing_portal.Session.create",
        return_value=session_mock,
    )

    resp = auth_client(picker_user).post("/stripe/customer-portal")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"url": "https://billing.stripe.com/session/test_url"}
    portal_create.assert_called_once()
    _, kwargs = portal_create.call_args
    assert kwargs["customer"] == "cus_test_existing"
    assert kwargs["return_url"] == "zelbi://settings"


def test_customer_portal_creates_customer_when_absent(
    auth_client, picker_user, db_session, mocker,
):
    assert picker_user.stripe_customer_id is None

    customer_mock = mocker.MagicMock()
    customer_mock.id = "cus_new_test"
    mocker.patch(
        "app.services.stripe_service.stripe.Customer.create",
        return_value=customer_mock,
    )

    session_mock = mocker.MagicMock()
    session_mock.url = "https://billing.stripe.com/session/new_url"
    portal_create = mocker.patch(
        "app.routers.stripe_billing.stripe.billing_portal.Session.create",
        return_value=session_mock,
    )

    resp = auth_client(picker_user).post("/stripe/customer-portal")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"url": "https://billing.stripe.com/session/new_url"}
    portal_create.assert_called_once()
    _, kwargs = portal_create.call_args
    assert kwargs["customer"] == "cus_new_test"
    assert kwargs["return_url"] == "zelbi://settings"


def test_customer_portal_401_when_unauthed(client):
    resp = client.post("/stripe/customer-portal")
    assert resp.status_code == 401
