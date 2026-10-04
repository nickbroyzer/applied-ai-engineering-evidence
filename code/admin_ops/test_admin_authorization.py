"""Admin router — require_admin guard on job-trigger endpoints."""


def test_non_admin_gets_403_on_expire_listings(auth_client, picker_user):
    resp = auth_client(picker_user).post("/admin/expire-listings")
    assert resp.status_code == 403


def test_admin_is_admitted_on_expire_listings(auth_client, db_session, picker_user):
    picker_user.is_admin = True
    db_session.add(picker_user)
    db_session.commit()

    resp = auth_client(picker_user).post("/admin/expire-listings")
    assert resp.status_code == 200
