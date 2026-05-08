import os, sys, asyncio

async def main():
    os.environ['LLM_PROVIDER'] = 'openai'
    os.environ['LLM_MODEL'] = 'deepseek-chat'
    os.environ['LLM_API_KEY'] = os.environ.get('DEEPSEEK_API_KEY', 'MISSING')
    os.environ['OPENAI_API_KEY'] = os.environ.get('DEEPSEEK_API_KEY', 'MISSING')
    os.environ['OPENAI_API_BASE'] = 'https://api.deepseek.com/v1'
    os.environ['EMBEDDING_PROVIDER'] = 'openai'
    os.environ['EMBEDDING_MODEL'] = 'deepseek-chat'
    os.environ['EMBEDDING_API_KEY'] = os.environ.get('DEEPSEEK_API_KEY', 'MISSING')
    os.environ['COGNEE_SKIP_CONNECTION_TEST'] = 'true'

    print(f"Provider: {os.environ['LLM_PROVIDER']}")
    print(f"Model: {os.environ['LLM_MODEL']}")
    print(f"API Key set: {'yes' if os.environ['LLM_API_KEY'] != 'MISSING' else 'NO - MISSING'}")

    # Test 1: LiteLLM direct call
    print("\n--- Test 1: LiteLLM direct ---")
    import litellm
    try:
        resp = litellm.completion(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Say ready"}],
            max_tokens=10,
        )
        print(f"OK: {resp.choices[0].message.content}")
    except Exception as e:
        print(f"FAIL: {e}")

    # Test 2: Cognee add + cognify
    print("\n--- Test 2: Cognee add + cognify ---")
    try:
        import cognee
        await cognee.add(["Russell uses DeepSeek for LLM and wants graph memory to work."])
        await cognee.cognify()
        print("OK: cognify completed")
    except Exception as e:
        print(f"FAIL: {e}")

    # Test 3: Cognee search
    print("\n--- Test 3: Cognee search ---")
    try:
        results = await cognee.search("DeepSeek LLM")
        print(f"OK: found {len(results)} results")
        for r in results[:3]:
            print(f"  - {str(r)[:200]}")
    except Exception as e:
        print(f"FAIL: {e}")

    print("\nDone.")

asyncio.run(main())
