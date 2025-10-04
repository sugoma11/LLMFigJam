import os
import cv2
import time
import base64
import nodriver as uc
from io import BytesIO
from langchain.schema import SystemMessage, HumanMessage

from core.base_runner import BaseRunner
from core.models import ImagesRequest
from runners.company_research.models import CompetitorAnalysisSpreadsheet, Products_reviews, Competitor, Reviews

class CompanyResearchRunner(BaseRunner):

    def __call__(self, *args, **kwds):
        return super().__call__(*args, **kwds)

    @staticmethod
    def get_competitors_sites(url_list: list[str]):

        async def main(url: str):

            browser = await uc.start(headless='new')

            page = await browser.get(url)
            await page.fullscreen()
            first = await page.find('accept')

            if first:
                await first.click()

            time.sleep(1)
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

    def fill_tables(self, url_list):
        to_figma_messages = []
        pydantic_containers_dict = {Competitor: CompetitorAnalysisSpreadsheet, Reviews: Products_reviews}
        for schema, container in pydantic_containers_dict.items():
            filled_schemas = {}
            for url in url_list:
                structured_model = self.model.with_structured_output(schema)
                schema_description = self.to_llm_message(schema, **{'company_name': url})
                response = structured_model.invoke([
                    SystemMessage(content="You are a helpful assistant that extracts structured data."),
                    HumanMessage(content=f"Use search to fill the schema: {schema_description}")
                ])
                filled_schemas[url] = response.model_dump()
            container_field = container.get_container_field()
            to_figma_messages.extend(container(**{container_field: filled_schemas}).to_figma_messages({'Company': self.pipeline_vars['company_name']}))

        return to_figma_messages

    def hook_after(self):

        url_list = self.llm_response.Url_List
        saved_sites_messages = self.get_competitors_sites(url_list)
        table_messages = self.fill_tables(url_list)

        return table_messages + saved_sites_messages
