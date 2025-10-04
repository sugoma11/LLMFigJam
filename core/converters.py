from abc import ABC, abstractmethod
from typing import Any, Dict, List, get_args, get_origin, Union


from core.models import (  # Import request models for type safety
    ColumnOfStickersRequest,
    StickerRequest,
    TableRequest,
)

class ContainerFieldMixin:
    @classmethod
    def get_container_field(cls) -> str:
        """
        Return the name of the single top-level field that is a dict container.
        """
        for name, field in cls.model_fields.items():
            anno = field.annotation
            origin = get_origin(anno)

            # unwrap Optional/Union[..., NoneType]
            if origin is Union:
                args = [a for a in get_args(anno) if a is not type(None)]
                if args:
                    anno = args[0]
                    origin = get_origin(anno)

            if origin in (dict, Dict):
                return name

        raise ValueError(f"No dict container field found in {cls.__name__}")



class FigmaConverter():

    def get_figma_key_mapping(self) -> Dict[str, str]:
        """Return mapping of field names to their Figma representation keys

        Example for company_research runner:
        return {
            'CompetitorAnalysisSpreadsheet': 'Company',
            'Products_reviews': 'Product'
        }
        """
        pass

    def to_figma_messages(self, table_request_sort_dict=None) -> list:
        """Generate Figma objects with configurable key mapping"""
        figma_objects = []
        key_mapping = self.get_figma_key_mapping()

        for field_name, field_value in self.model_dump(exclude_unset=True).items():
            if field_value is None:
                continue

            topic_title = field_name.replace('_', ' ').title()

            if isinstance(field_value, str):
                figma_objects.append(StickerRequest(topicTitle=topic_title, content=field_value).model_dump())

            elif isinstance(field_value, list):

                figma_objects.append(ColumnOfStickersRequest(
                    topicTitle=topic_title,
                    content=field_value,
                    spacing=220 + ((len(field_value) // 200) * 1550)
                ).model_dump())

            elif isinstance(field_value, dict):
                # Use field-specific key from mapping, or default to generic key
                dict_key = key_mapping[field_name]

                figma_objects.append(TableRequest(
                    topicTitle=topic_title,
                    content=[{dict_key: item_name, **item_data} for item_name, item_data in field_value.items()]
                    # for company_research: dict_key == a common column title like company, product
                    # item_name == company name, item_data == Dict[str, str] with content
                ).sort(table_request_sort_dict).model_dump()) # sort by the value in the dict if provided. e.g, in company_research, sort by main company name

        return figma_objects
