from typing import Any, Type, Dict

from pydantic import (
    BaseModel,
    Field,
    ImportString,
)

from collections.abc import Callable
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_key: str = Field(description="LLM providers' api key")
    api_url: str = Field(description="LLM providers' api base url")
    model: str = Field(description="Model name in provider:model format of openrouter")
    temperature: float = Field(description='Temperature of LLM output generation')

    prompts: ImportString#[Type[str]] = Field(description='Prompts for LLM inference')
    pipeline_vars: Dict # = Field(description='Prompts for LLM inference')
    response_schema: ImportString[Type[BaseModel]] = Field(description='Response schema for structured LLM return')
    pdf_loader: ImportString[Callable[[Any], Any]] = Field(description='PDF text loader')
    pdf_path: str = Field(description='Path to the PDF (if we have one)')
    runner: ImportString[Type[Any]] = Field(description='Pipeline runner class to use')
    model_config = SettingsConfigDict(env_file='.env')
