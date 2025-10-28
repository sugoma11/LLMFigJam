"""Integration test for CompanyResearchRunner.

This test runs the complete pipeline with:
- Real LLM API calls
- Real PDF loading
- Mocked web scraping (get_competitors_sites)
- Validation of returned message structure
"""
import pytest
from unittest.mock import patch, MagicMock

from runners.company_research.runner import CompanyResearchRunner


@pytest.fixture
def mock_web_scraping(mocker):
    """Mock the web scraping functionality to avoid browser automation."""
    mock = mocker.patch(
        'runners.company_research.runner.CompanyResearchRunner.get_competitors_sites',
        return_value=[]
    )
    return mock


@pytest.fixture
def mock_fill_tables(mocker):
    """Mock the fill_tables method to avoid additional LLM calls for competitor analysis."""
    mock = mocker.patch(
        'runners.company_research.runner.CompanyResearchRunner.fill_tables',
        return_value=[]
    )
    return mock


def test_company_research_runner_integration(
    test_llm_model,
    test_schema,
    test_prompts,
    pdf_loader,
    test_pipeline_vars,
    test_pdf_path,
    mock_web_scraping,
    mock_fill_tables
):
    """
    Integration test for the complete CompanyResearchRunner pipeline.

    This test:
    1. Loads a real PDF file
    2. Makes real LLM API calls (not mocked)
    3. Processes the response through the pipeline
    4. Returns a list of messages suitable for FigJam
    5. Validates message structure and content
    """
    # Initialize the runner with all components
    runner = CompanyResearchRunner(
        model=test_llm_model,
        response_schema=test_schema,
        prompts=test_prompts,
        pdf_loader=pdf_loader,
        pipeline_vars=test_pipeline_vars,
        pdf_path=test_pdf_path,
        dump_results=False  # Don't dump results during testing
    )

    # Run the complete pipeline
    messages = runner.run()

    # Assertions
    # 1. Check that we got a list of messages back
    assert isinstance(messages, list), "Runner should return a list of messages"
    assert len(messages) > 0, "Runner should return at least one message"

    # 2. Validate message structure
    for message in messages:
        assert isinstance(message, dict), "Each message should be a dictionary"

        # All messages should have these required fields
        assert "type" in message, "Message should have a 'type' field"
        assert "topicTitle" in message, "Message should have a 'topicTitle' field"

        # Validate type is one of the expected values
        assert message["type"] in [
            "addSticker",
            "addTable",
            "addStickerColumn",
            "addImages"
        ], f"Message type should be one of the expected types, got: {message['type']}"

        assert isinstance(message["topicTitle"], str), "topicTitle should be a string"
        assert len(message["topicTitle"]) > 0, "topicTitle should not be empty"

        # Validate content exists and is appropriate for the type
        if message["type"] == "addSticker":
            assert "content" in message, "addSticker should have content"
            assert isinstance(message["content"], str), "addSticker content should be a string"

        elif message["type"] == "addStickerColumn":
            assert "content" in message, "addStickerColumn should have content"
            assert isinstance(message["content"], list), "addStickerColumn content should be a list"

        elif message["type"] == "addTable":
            assert "content" in message, "addTable should have content"
            assert isinstance(message["content"], list), "addTable content should be a list"
            if len(message["content"]) > 0:
                # Each row should be a dictionary
                assert isinstance(message["content"][0], dict), "Table rows should be dictionaries"

    # 3. Validate that we have expected message types based on the schema
    message_types = {msg["type"] for msg in messages}

    # Based on MarketResearch schema, we expect at least some Stickers or addStickerColumn
    assert len(message_types & {"addSticker", "addTable", "addStickerColumn", "addImages"}) > 0, \
        "Should have at least one of: addSticker, addStickerColumn, or addTable"

    # 4. Validate that topicTitles are properly formatted
    topic_titles = [msg["topicTitle"] for msg in messages]

    for title in topic_titles:
        assert "_" not in title, f"Topic title should not contain underscores: {title}"

    # 5. visible with pytest -v -s
    print(f"\n\nTest Summary:")
    print(f"  Total messages: {len(messages)}")
    print(f"  Message types: {message_types}")
    print(f"  Topic titles: {topic_titles}")

    assert runner.llm_response is not None, "Runner should store the LLM response"

    print(f"\n  Web scraping mocked: {mock_web_scraping.called}")
    print(f"  Fill tables mocked: {mock_fill_tables.called}")
