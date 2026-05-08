import os, asyncio, time
os.environ['LLM_PROVIDER'] = 'deepseek'
os.environ['LLM_API_KEY'] = os.environ.get('DEEPSEEK_API_KEY','')
os.environ['LLM_MODEL'] = 'deepseek-chat'
os.environ['LLM_ENDPOINT'] = 'https://api.deepseek.com/v1'
os.environ['COGNEE_SKIP_CONNECTION_TEST'] = 'true'

from cognee.infrastructure.llm import get_llm_config
config = get_llm_config()
print(f'provider={config.llm_provider} model={config.llm_model} key_set={bool(config.llm_api_key)}')

async def main():
    from cognee.infrastructure.llm.structured_output_framework.litellm_instructor.llm.get_llm_client import get_llm_client
    from pydantic import BaseModel
    class TM(BaseModel):
        answer: str
    
    start = time.time()
    client = get_llm_client()
    print(f'client={type(client).__name__} in {time.time()-start:.0f}s')
    
    start = time.time()
    r = await client.acreate_structured_output(
        text_input='What is 2+2?',
        system_prompt='Output valid JSON with field "answer". Include word JSON.',
        response_model=TM,
    )
    print(f'OK {time.time()-start:.0f}s: {r.answer}')

asyncio.run(main())
