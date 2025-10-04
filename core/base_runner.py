import json
import time
import requests
from datetime import datetime
from typing import Dict, Optional, Callable
from langchain.schema import SystemMessage, HumanMessage

from runners.company_research.models import MarketResearch

# may be the TemplateMethod is a wrong pattern here as the subclasses has a lot of different logic in the hooks
class BaseRunner():

    def __init__(self, model, response_schema: Optional[MarketResearch], prompts, pdf_loader: Callable[[str], str],
                  pipeline_vars: Dict, pdf_path: str = None, dump_results: bool = True):

        self.model = model
        self.prompts = prompts
        self.pipeline_vars = pipeline_vars # rename to pipeline_vars
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

    def push_to_queue(self, messages):

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
            system_prompt = self.prompts.system_prompt
        else:
            pdf_text = ''
            system_prompt = self.prompts.no_pdf_system_prompt

        schema_description = self.to_llm_message(self.response_schema, **self.pipeline_vars)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=('\n'.join((pdf_text, schema_description))).strip())
        ]

        self.llm_response = self.model.with_structured_output(self.response_schema).invoke(messages)
        self.messages_to_figma += self.llm_response.to_figma_messages()

        self.messages_to_figma += self.hook_after()

        if self.dump_results:
            with open(f'to-figma-messages-{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.json', 'w') as f:
                json.dump(self.messages_to_figma, f, indent=2)

        return self.messages_to_figma