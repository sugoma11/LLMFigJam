from langchain_openai import ChatOpenAI

from server.main import start_server
from core.settings import Settings

if __name__ == "__main__":
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

    _, thread = start_server(host="0.0.0.0", port=8000, messages=messages)

    try:
        thread.join()
    except KeyboardInterrupt:
        print("Shutting down server...")
