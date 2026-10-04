from app.services.ai_service import ListingAIAnalysis, ListingAIResult


def test_analyze_photo_403_when_key_prefixed_with_other_user_id(
    mocker, auth_client, giver_user, picker_user,
):
    mock_analyze = mocker.patch("app.routers.ai.analyze_listing_image")

    resp = auth_client(giver_user).post(
        "/ai/analyze-photo",
        json={"object_key": f"{picker_user.id}/photo.jpg"},
    )

    assert resp.status_code == 403
    mock_analyze.assert_not_called()


def test_analyze_photo_passes_ownership_check_with_own_id(
    mocker, auth_client, giver_user,
):
    mocker.patch(
        "app.routers.ai.analyze_listing_image",
        return_value=ListingAIAnalysis(
            option_a=ListingAIResult(title="A", description="A desc", category="Other"),
            option_b=ListingAIResult(title="B", description="B desc", category="Other"),
            confidence="high",
        ),
    )

    resp = auth_client(giver_user).post(
        "/ai/analyze-photo",
        json={"object_key": f"{giver_user.id}/photo.jpg"},
    )

    assert resp.status_code == 200, resp.text
