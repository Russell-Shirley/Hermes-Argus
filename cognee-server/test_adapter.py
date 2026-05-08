import os, asyncio
os.environ['LLM_PROVIDER'] = 'deepseek'
os.environ['LLM_API_KEY'] = os.environ.get('DEEPSEEK_API_KEY', '')
os.environ['COGNEE_SKIP_CONNECTION_TEST'] = 'true'

async def main():
    from cognee.infrastructure.llm.structured_output_framework.litellm_instructor.llm.get_llm_client import get_llm_client
    from pydantic import BaseModel
    class TestModel(BaseModel):
        answer: str
    
    client = get_llm_client()
    print(f'Client: {type(client).__name__}')
    result = await client.acreate_structured_output(
        text_input='What is 2+2?',
        system_prompt='You must output valid JSON. Return a JSON object with field "answer". Output format: {"answer": "your answer"}',
        response_model=TestModel,
    )
    print(f'OK: {result}')

asyncio.run(main())
