from app.services.ai_service import (
    ListingAIAnalysis,
    ListingAIResult,
)


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
