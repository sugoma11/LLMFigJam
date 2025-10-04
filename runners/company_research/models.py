from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from core.converters import ContainerFieldMixin, FigmaConverter


class Competitor(BaseModel, FigmaConverter):
    USP: Optional[str] = Field(None, description="Define Unique Selling Proposition of {company_name} - what makes them stand out from competitors")
    Strengths: Optional[str] = Field(None, description="Define Strengs of {company_name} - list 3-5 main competitive advantages")
    Weaknesses: Optional[str] = Field(None, description="Define Weaknesses of {company_name} - list 3-5 areas where they lag behind competitors")
    Target_Market: Optional[str] = Field(None, description="Primary target market for {company_name} - describe the main customer segment they serve")
    User_Profiles: Optional[str] = Field(None, description="Typical user profiles for {company_name} - list 2-4 types of users who commonly use their product")
    Main_Use_Cases: Optional[str] = Field(None, description="Primary use cases for {company_name}'s product - list 3-5 main ways customers use their solution")

class CompetitorAnalysisSpreadsheet(ContainerFieldMixin, BaseModel, FigmaConverter):
    Competitor_Table: Optional[Dict[str, Competitor]] = Field(...) # , description="Provide a competitor analysis spreadsheet with mentioned {competitors_urls}. Include USPs, Strengths, Weaknesses, Target market, Prevailing user (who typically uses it), Main use cases (how users apply the product). "

    def get_figma_key_mapping(self) -> Dict[str, str]:
        return {'Competitor_Table': 'Company'}

class Reviews(BaseModel, FigmaConverter):
    Five_Star_Reviews: Optional[str] = Field(None, description='Provide positive (5 stars) reviews for {company_name}. Find user reviews on platforms like TrustPilot, Clutch, Google Reviews, Reddit, and other web sources')
    Two_Star_Reviews: Optional[str] = Field(None, description='Provide negative (1-2 stars) reviews for {company_name}. Find user reviews on platforms like TrustPilot, Clutch, Google Reviews, Reddit, and other web sources')


class Products_reviews(ContainerFieldMixin, BaseModel, FigmaConverter):
    Rewies: Optional[Dict[str, Reviews]] = Field(None)

    def get_figma_key_mapping(self) -> Dict[str, str]:
        return {'Rewies': 'Company'}

class MarketResearch(BaseModel, FigmaConverter):
    General: Optional[str] = Field(None, description="Define {company_name} mission")
    Values: Optional[List[str]] = Field(None, description="Define values a {company_name} wants to communicate or already communicates")
    Category: Optional[str] = Field(None, description="Which business model (B2B, B2C, B2G, ...) is {company_name}")

    User_profiles: Optional[List[str]] = Field(None, description="Describe the main users of the product based on the provided document. "
                                                                 "Analyze provided document, conduct online research. Describe potential users who might also be a good fit for the product. "
                                                                 "If no user data is available, make an educated assumption and state: 'I assume users for this product could look like this...'")

    Top_problems: Optional[List[str]] = Field(None, description="Provide a detailed analysis of user problems related to {company_name} product, focusing on where they struggle the most with existing solutions in this niche. "
                                                                "Examine the provided document and conduct online research to gather insights. List the top 3 problems faced by each type of user.")

    General_Problems: Optional[List[str]] = Field(None, description="Create a generalized list of additional common problems by:\n"
                                                                    "Making informed assumptions about the niche\n"
                                                                    "Using insights from internet resources\n"
                                                                    "Sorting the problems by relevance to {company_name} product.")

    Use_cases: Optional[List[str]] = Field(None, description="Describe the most popular use cases of the {company_name} product. Also, if applicable, describe use cases that a competitor has, add it to the end and start with 'Competitors use case: ...'.")

    Traffic_Sources: Optional[List[str]] = Field(None, description="Analyze the provided document to determine how people currently find the product.\n"
                                                                   "Conduct online research to uncover how users discover competitor products in the same niche.\n"
                                                                   "Return the top 3 traffic sources that would be most valuable for {company_name} product.")

    Offers: Optional[List[str]] = Field(None, description="Suggest how {company_name} updated USP could look based on the analysis. Create three high-converting offers that align with: USP, User Profiles, User Problems, Product Features.")

    Url_List: Optional[List[str]] = Field(None, description="Find URLs related of {company_name} competitors. Use the provided document if available or online research. Return 4 URLs only.",
                                          exclude=True)


if __name__ == '__main__':
    import json
    import pprint
    tt = MarketResearch().to_llm_message(**{'company_name': 'Test', "competitors_urls": ['barbri.com', 'themisbar.com']})
    print(tt)
    # pprint.pprint(tt)
    # pprint.pprint(tt.to_figma_messages())