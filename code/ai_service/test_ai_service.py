import io

import pytest
from botocore.exceptions import ClientError

from app.services.ai_service import (
    AIServiceError,
    ListingAIAnalysis,
    ListingAIResult,
    ReadabilityResult,
    analyze_listing_image,
    check_listing_image_readability,
)


def test_analyze_listing_image_returns_ab_pair_and_confidence(mocker):
    mock_s3 = mocker.MagicMock()
    mock_s3.get_object.return_value = {
        "Body": io.BytesIO(b"fake_image_bytes"),
    }
    mocker.patch("app.services.ai_service.boto3.client", return_value=mock_s3)

    text = (
        '{"option_a": {"title": "Vintage Singer 99K Sewing Machine", '
        '"description": "Black enamel Singer 99K sewing machine, working condition.", '
        '"category": "Appliances"}, '
        '"option_b": {"title": "Sewing machine", '
        '"description": "Sewing machine in working condition.", '
        '"category": "Appliances"}, '
        '"confidence": "high"}'
    )
    text_block = mocker.MagicMock()
    text_block.type = "text"
    text_block.text = text
    mock_message = mocker.MagicMock()
    mock_message.content = [text_block]

    mock_anthropic_instance = mocker.MagicMock()
    mock_anthropic_instance.messages.create.return_value = mock_message
    mocker.patch("app.services.ai_service.Anthropic", return_value=mock_anthropic_instance)

    result = analyze_listing_image("test-user/test-object.jpg")

    assert isinstance(result, ListingAIAnalysis)
    assert isinstance(result.option_a, ListingAIResult)
    assert isinstance(result.option_b, ListingAIResult)
    assert result.option_a.title == "Vintage Singer 99K Sewing Machine"
    assert result.option_a.category == "Appliances"
    assert result.option_b.title == "Sewing machine"
    assert result.option_b.category == "Appliances"
    assert result.confidence == "high"


def test_analyze_listing_image_anthropic_failure(mocker):
    mock_s3 = mocker.MagicMock()
    mock_s3.get_object.return_value = {
        "Body": io.BytesIO(b"fake_image_bytes"),
    }
    mocker.patch("app.services.ai_service.boto3.client", return_value=mock_s3)

    mock_anthropic_instance = mocker.MagicMock()
    mock_anthropic_instance.messages.create.side_effect = Exception(
        "simulated Anthropic API error"
    )
    mocker.patch("app.services.ai_service.Anthropic", return_value=mock_anthropic_instance)

    with pytest.raises(AIServiceError) as exc_info:
        analyze_listing_image("test-user/test-object.jpg")

    assert "Anthropic API request failed" in str(exc_info.value)


def test_analyze_listing_image_invalid_confidence_rejected(mocker):
    mock_s3 = mocker.MagicMock()
    mock_s3.get_object.return_value = {
        "Body": io.BytesIO(b"fake_image_bytes"),
    }
    mocker.patch("app.services.ai_service.boto3.client", return_value=mock_s3)

    text = (
        '{"option_a": {"title": "T", "description": "D", "category": "Other"}, '
        '"option_b": {"title": "T", "description": "D", "category": "Other"}, '
        '"confidence": "very_high"}'
    )
    text_block = mocker.MagicMock()
    text_block.type = "text"
    text_block.text = text
    mock_message = mocker.MagicMock()
    mock_message.content = [text_block]

    mock_anthropic_instance = mocker.MagicMock()
    mock_anthropic_instance.messages.create.return_value = mock_message
    mocker.patch("app.services.ai_service.Anthropic", return_value=mock_anthropic_instance)

    with pytest.raises(AIServiceError) as exc_info:
        analyze_listing_image("test-user/test-object.jpg")

    assert "expected schema" in str(exc_info.value)


def test_analyze_listing_image_invalid_category_in_option_a(mocker):
    mock_s3 = mocker.MagicMock()
    mock_s3.get_object.return_value = {
        "Body": io.BytesIO(b"fake_image_bytes"),
    }
    mocker.patch("app.services.ai_service.boto3.client", return_value=mock_s3)

    text = (
        '{"option_a": {"title": "T", "description": "D", "category": "Vehicles"}, '
        '"option_b": {"title": "T", "description": "D", "category": "Other"}, '
        '"confidence": "medium"}'
    )
    text_block = mocker.MagicMock()
    text_block.type = "text"
    text_block.text = text
    mock_message = mocker.MagicMock()
    mock_message.content = [text_block]

    mock_anthropic_instance = mocker.MagicMock()
    mock_anthropic_instance.messages.create.return_value = mock_message
    mocker.patch("app.services.ai_service.Anthropic", return_value=mock_anthropic_instance)

    with pytest.raises(AIServiceError) as exc_info:
        analyze_listing_image("test-user/test-object.jpg")

    assert "option_a" in str(exc_info.value)
    assert "Vehicles" in str(exc_info.value)


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


def _mock_r2_success(mocker):
    mock_s3 = mocker.MagicMock()
    mock_s3.get_object.return_value = {
        "Body": io.BytesIO(b"fake_image_bytes"),
    }
    mocker.patch("app.services.ai_service.boto3.client", return_value=mock_s3)
    return mock_s3


def test_check_readability_pass(mocker):
    _mock_r2_success(mocker)
    _mock_anthropic_text(mocker, '{"readable": true, "reason": null}')

    result = check_listing_image_readability("test-user/test-object.jpg")

    assert isinstance(result, ReadabilityResult)
    assert result.readable is True
    assert result.reason is None


def test_check_readability_fail_with_reason(mocker):
    _mock_r2_success(mocker)
    _mock_anthropic_text(
        mocker,
        '{"readable": false, "reason": "image is too blurry to identify the object"}',
    )

    result = check_listing_image_readability("test-user/test-object.jpg")

    assert isinstance(result, ReadabilityResult)
    assert result.readable is False
    assert result.reason == "image is too blurry to identify the object"


def test_check_readability_anthropic_failure(mocker):
    _mock_r2_success(mocker)

    mock_anthropic_instance = mocker.MagicMock()
    mock_anthropic_instance.messages.create.side_effect = Exception(
        "simulated Anthropic API error"
    )
    mocker.patch("app.services.ai_service.Anthropic", return_value=mock_anthropic_instance)

    with pytest.raises(AIServiceError) as exc_info:
        check_listing_image_readability("test-user/test-object.jpg")

    assert "Anthropic API request failed" in str(exc_info.value)


def test_check_readability_r2_fetch_failure(mocker):
    mock_s3 = mocker.MagicMock()
    mock_s3.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "key not found"}},
        "GetObject",
    )
    mocker.patch("app.services.ai_service.boto3.client", return_value=mock_s3)

    with pytest.raises(AIServiceError) as exc_info:
        check_listing_image_readability("test-user/missing.jpg")

    assert "R2 object fetch failed" in str(exc_info.value)
