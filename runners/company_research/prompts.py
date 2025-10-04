# TODO: 'I wasn't able to find information about [topic]' is not working and just eats tokens

system_prompt = """{company_name} wants to update their website, and I need top-tier research at the level of McKinsey.com and Ogilvy.com. I’ll break down the research into different areas, each with a dedicated message containing specific prompts.
How this will work:
Below is a questionnaire that {company_name} has filled out.
You’ll conduct research using:
- The PDF (or any other files I provide).
- Online sources. Browse the web where needed.
- User reviews from relevant sources (essential).
If any key information is missing, let me know by saying: "I wasn't able to find information about [topic]. Ask {company_name} about [specific questions]."
"""

no_pdf_system_prompt = """{company_name} wants to update their website, and I need top-tier research at the level of McKinsey.com and Ogilvy.com. I’ll break down the research into different areas, each with a dedicated message containing specific prompts.
You’ll conduct research using:
 - Use search to fill research sections about {company_name}.
 - Include user reviews from relevant sources (essential).
If any key information is missing, let me know by saying: "I wasn't able to find information about [topic]".
"""

