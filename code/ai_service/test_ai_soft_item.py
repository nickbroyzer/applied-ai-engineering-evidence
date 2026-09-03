import io

from app.services.ai_service import ListingAIAnalysis, analyze_listing_image


def _mock_r2_success(mocker):
    mock_s3 = mocker.MagicMock()
    mock_s3.get_object.return_value = {
        "Body": io.BytesIO(b"fake_image_bytes"),
    }
    mocker.patch("app.services.ai_service.boto3.client", return_value=mock_s3)
    return mock_s3


def _mock_anthropic_text(mocker, text: str):
    text_block = mocker.MagicMock()
    text_block.type = "text"
    text_block.text = text
    mock_message = mocker.MagicMock()
    mock_message.content = [text_block]

    mock_anthropic_instance = mocker.MagicMock()
    mock_anthropic_instance.messages.create.return_value = mock_message
    mocker.patch("app.services.ai_service.Anthropic", return_value=mock_anthropic_instance)
    return mock_anthropic_instance


def test_soft_item_true_survives_parse(mocker):
    _mock_r2_success(mocker)
    text = (
        '{"option_a": {"title": "T", "description": "D", "category": "Other"}, '
        '"option_b": {"title": "T", "description": "D", "category": "Other"}, '
        '"confidence": "high", "soft_item": true}'
    )
    _mock_anthropic_text(mocker, text)

    result = analyze_listing_image("test-user/test-object.jpg")

    assert isinstance(result, ListingAIAnalysis)
    assert result.soft_item is True


def test_soft_item_false_parses_as_false(mocker):
    _mock_r2_success(mocker)
    text = (
        '{"option_a": {"title": "T", "description": "D", "category": "Other"}, '
        '"option_b": {"title": "T", "description": "D", "category": "Other"}, '
        '"confidence": "high", "soft_item": false}'
    )
    _mock_anthropic_text(mocker, text)

    result = analyze_listing_image("test-user/test-object.jpg")

    assert result.soft_item is False


def test_soft_item_missing_key_defaults_to_false(mocker):
    _mock_r2_success(mocker)
    text = (
        '{"option_a": {"title": "T", "description": "D", "category": "Other"}, '
        '"option_b": {"title": "T", "description": "D", "category": "Other"}, '
        '"confidence": "high"}'
    )
    _mock_anthropic_text(mocker, text)

    result = analyze_listing_image("test-user/test-object.jpg")

    assert result.soft_item is False
