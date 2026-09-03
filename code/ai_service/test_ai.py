from app.services.ai_service import (
    AIServiceError,
    ListingAIAnalysis,
    ListingAIResult,
    ReadabilityResult,
)


def test_post_check_readability_authenticated_pass(mocker, auth_client, giver_user):
    mocker.patch(
        "app.routers.ai.check_listing_image_readability",
        return_value=ReadabilityResult(readable=True, reason=None),
    )

    resp = auth_client(giver_user).post(
        "/ai/check-readability",
        json={"object_key": f"{giver_user.id}/test-object.jpg"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {"readable": True, "reason": None}


def test_post_check_readability_authenticated_fail(mocker, auth_client, giver_user):
    mocker.patch(
        "app.routers.ai.check_listing_image_readability",
        return_value=ReadabilityResult(readable=False, reason="too blurry"),
    )

    resp = auth_client(giver_user).post(
        "/ai/check-readability",
        json={"object_key": f"{giver_user.id}/blurry.jpg"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {"readable": False, "reason": "too blurry"}


def test_post_check_readability_unauthenticated_401(client):
    resp = client.post(
        "/ai/check-readability",
        json={"object_key": "test-user/test-object.jpg"},
    )

    assert resp.status_code == 401


def test_post_check_readability_502_on_aiserviceerror(mocker, auth_client, giver_user):
    mocker.patch(
        "app.routers.ai.check_listing_image_readability",
        side_effect=AIServiceError("simulated R2 fetch failure"),
    )

    resp = auth_client(giver_user).post(
        "/ai/check-readability",
        json={"object_key": f"{giver_user.id}/test-object.jpg"},
    )

    assert resp.status_code == 502
    assert resp.json() == {"detail": "AI service temporarily unavailable"}


def test_post_check_readability_422_on_missing_object_key(auth_client, giver_user):
    resp = auth_client(giver_user).post(
        "/ai/check-readability",
        json={},
    )

    assert resp.status_code == 422


def test_post_analyze_photo_returns_ab_shape(mocker, auth_client, giver_user):
    mocker.patch(
        "app.routers.ai.analyze_listing_image",
        return_value=ListingAIAnalysis(
            option_a=ListingAIResult(
                title="Vintage Singer 99K Sewing Machine",
                description="Black enamel Singer 99K, working condition.",
                category="Appliances",
            ),
            option_b=ListingAIResult(
                title="Sewing machine",
                description="Sewing machine in working condition.",
                category="Appliances",
            ),
            confidence="high",
        ),
    )

    resp = auth_client(giver_user).post(
        "/ai/analyze-photo",
        json={"object_key": f"{giver_user.id}/test-object.jpg"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) == {"option_a", "option_b", "confidence", "soft_item"}
    assert body["option_a"]["title"] == "Vintage Singer 99K Sewing Machine"
    assert body["option_a"]["category"] == "Appliances"
    assert body["option_b"]["title"] == "Sewing machine"
    assert body["option_b"]["category"] == "Appliances"
    assert body["confidence"] == "high"
