import os
import json
import time
import requests
from types import ModuleType
from datetime import datetime
from typing import Dict, Optional, Callable, Union, List
from langchain.schema import SystemMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel

from core.models import TableRequest, StickerRequest, ColumnOfStickersRequest
from runners.company_research.models import MarketResearch

# may be the TemplateMethod is a wrong pattern here as there is one subclasses with a lot of different logic in the hooks
class BaseRunner():

    def __init__(self, model: BaseChatModel, response_schema: Optional[MarketResearch], prompts: Union[ModuleType, Dict, str],
                pdf_loader: Callable[[str], str], pipeline_vars: Dict = None, pdf_path: str = None,
                dump_results: bool = True):

        self.model = model
        self.prompts = prompts
        self.pipeline_vars = pipeline_vars
        self.pdf_path = pdf_path
        self.pdf_loader = pdf_loader
        self.response_schema = response_schema

        self.messages_to_figma = []
        self.llm_response = None
        self.dump_results = dump_results

    @staticmethod
    def to_llm_message(cls, **kwargs) -> str:
        lines = []
        for name, field in cls.__fields__.items():
            desc = field.description
            if desc:
                lines.append(f"{name}: {desc.format(**kwargs)}")
        return "\n".join(lines)

    @staticmethod
    def get_prompt(prompts: Union[ModuleType, Dict, str], pdf_path: str):

        if pdf_path:
            key = "system_prompt"
        else:
            key = "no_pdf_system_prompt"

        if isinstance(prompts, dict):
            return prompts.get(key)
        elif isinstance(prompts, ModuleType):
            return getattr(prompts, key, None)
        elif isinstance(prompts, str):
            return prompts

    @staticmethod
    def to_figma_messages(response, table_request_sort_dict: Dict =None) -> list:
        """Generate Figma objects with configurable key mapping"""
        figma_objects = []

        for field_name, field_value in response.model_dump(exclude_unset=True).items():
            if field_value is None:
                continue

            topic_title = field_name.replace('_', ' ').title()

            if isinstance(field_value, str):
                figma_objects.append(StickerRequest(topicTitle=topic_title, content=field_value).model_dump())

            elif isinstance(field_value, list):

                figma_objects.append(ColumnOfStickersRequest(
                                        topicTitle=topic_title,
                                        content=field_value,
                                    ).model_dump()) # does model dump have any sense?

            elif isinstance(field_value, dict):
                print(f'{field_value=}')
                print(f'{field_name=}')
                transformed_list = [{field_name: inner_key, **inner_value} for inner_key, inner_value in field_value.items()]

                figma_objects.append(TableRequest(
                    topicTitle=topic_title,
                    content=transformed_list,
                ).sort(table_request_sort_dict).model_dump()) # sort by the value in the dict if provided. e.g, in company_research, sort by main company name


        return figma_objects

    def push_to_queue(self, messages: List[Dict]):

        for m in messages:
            _ = requests.post(
                "http://localhost:8000/push",
                json=m.model_dump()
            )

        time.sleep(1)

    def hook_before(self):
        return []

    def hook_after(self):
        return []

    def run(self):

        self.messages_to_figma += self.hook_before()

        if self.pdf_path:
            pdf_text = self.pdf_loader(self.pdf_path)
        else:
            pdf_text = ''

        system_prompt = self.get_prompt(self.prompts, self.pdf_path)

        schema_description = self.to_llm_message(self.response_schema, **self.pipeline_vars)

        messages = [
            SystemMessage(content=system_prompt.format(**self.pipeline_vars)),
            HumanMessage(content=('\n'.join((pdf_text, schema_description))).strip())
        ]

        self.llm_response = self.model.with_structured_output(self.response_schema).invoke(messages)
        self.messages_to_figma += self.to_figma_messages(self.llm_response)

        self.messages_to_figma += self.hook_after()

        if self.dump_results:
            if not os.path.isdir('llm_responses'):
                os.mkdir('llm_responses')
            with open(f'llm_responses/to-figma-messages-{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.json', 'w') as f:
                json.dump(self.messages_to_figma, f, indent=2)

        return self.messages_to_figma
