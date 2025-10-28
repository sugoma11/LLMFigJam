"""Pytest configuration and fixtures for integration tests."""
import os
import pytest
from pathlib import Path
from langchain_openai import ChatOpenAI

from core.loaders import get_pdf_plumber_message
from runners.company_research.models import MarketResearch
from runners.company_research import prompts


@pytest.fixture
def test_pdf_path():
    """Return path to test PDF file."""
    return str(Path(__file__).parent / "fixtures" / "sample.pdf")


@pytest.fixture
def test_schema():
    """Return the MarketResearch schema for testing."""
    return MarketResearch


@pytest.fixture
def test_prompts():
    """Return the prompts module for testing."""
    return prompts


@pytest.fixture
def test_pipeline_vars():
    """Return pipeline variables for testing."""
    return {
        "company_name": "BPH",
        "competitors_urls": ["barbri.com", "themisbar.com"]
    }


@pytest.fixture
def test_llm_model():
    """
    Return configured ChatOpenAI model for testing.
    Requires environment variables:
    - OPENAI_API_KEY
    - OPENAI_API_BASE (optional)
    - MODEL_NAME (optional, defaults to gpt-4o-mini)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")

    api_base = os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    model_name = os.getenv("MODEL_NAME", "x-ai/grok-4-fast:free")
    temperature = float(os.getenv("TEMPERATURE", "0.7"))

    return ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        openai_api_base=api_base,
        temperature=temperature
    )


@pytest.fixture
def pdf_loader():
    """Return the PDF loader function."""
    return get_pdf_plumber_message
