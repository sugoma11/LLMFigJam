import os
import cv2
import time
import base64
import nodriver as uc
from io import BytesIO
from typing import List
from langchain.schema import SystemMessage, HumanMessage

from core.base_runner import BaseRunner
from core.models import ImagesRequest
from runners.company_research.models import Competitor_table, Products_reviews, Competitor, Reviews

class CompanyResearchRunner(BaseRunner):

    def __call__(self, *args, **kwds):
        return super().__call__(*args, **kwds)

    @staticmethod
    def get_competitors_sites(url_list: List[str]):

        async def main(url: str):

            browser = await uc.start(headless=True)

            page = await browser.get(url)
            await page.fullscreen()
            first = await page.find('accept')

            if first:
                await first.click()

            time.sleep(1)
            # here we have to deal with saving in the fs because of the nodriver implementation
            await page.save_screenshot(filename='temp.png', full_page=True)

        return_image_list = [] # will already contain objects send to figma
        for i, url in enumerate(url_list):
            uc.loop().run_until_complete(main(url))
            site_screenshot = cv2.imread('temp.png')

            crops = []
            for j in range(0, site_screenshot.shape[0] // 720 + 1):
                tile = site_screenshot[j*720: j*720 + 720, :, :]
                _, buffer = cv2.imencode('.jpg', tile)
                io_buf = BytesIO(buffer)
                img_str = base64.b64encode(io_buf.getvalue()).decode("utf-8").strip('"')
                crops.append(img_str)

            return_image_list.append(ImagesRequest(topicTitle=f'Competitor {i+1}', content=crops).model_dump())

        os.remove('temp.png')

        return return_image_list

    def fill_tables(self, url_list: List[str]):
        to_figma_messages = []
        schemas_to_fill = {Competitor: Competitor_table, Reviews: Products_reviews}
        for schema, container in schemas_to_fill.items():
            filled_schemas = {}
            for url in url_list:
                # run in separate invokes for every single dict to low hallucionations
                structured_model = self.model.with_structured_output(schema)
                schema_description = self.to_llm_message(schema, **{'company_name': url})
                response = structured_model.invoke([
                    SystemMessage(content="You are a helpful assistant that extracts structured data."),
                    HumanMessage(content=f"Use search to fill the schema: {schema_description}")
                ])
                filled_schemas[url] = response.model_dump() # and below sort so the target company will be the first in the tables
            to_figma_messages.extend(self.to_figma_messages(container(**{container.__name__: filled_schemas}), {container.__name__: self.pipeline_vars['company_name']}))

        return to_figma_messages


    def hook_after(self):

        if hasattr(self.llm_response, 'url_list'):
            url_list = self.llm_response.url_list
            saved_sites_messages = self.get_competitors_sites(url_list)
            table_messages = self.fill_tables(url_list)
            return table_messages + saved_sites_messages

        return []


if __name__ == "__main__":
    from langchain_openai import ChatOpenAI
    from core.settings import Settings

    settings = Settings()

    model = ChatOpenAI(
        model=settings.model,
        openai_api_key=settings.api_key,
        openai_api_base=settings.api_url,
        temperature=settings.temperature
    )

    response_schema = settings.response_schema

    pdf_loader = settings.pdf_loader
    pdf_path = settings.pdf_path
    prompts = settings.prompts
    pipeline_vars = settings.pipeline_vars if hasattr(settings, 'pipeline_vars') else {}


    runner = settings.runner(model, response_schema, prompts, pdf_loader, pipeline_vars, pdf_path)

    messages = runner.run()

    print(messages)
