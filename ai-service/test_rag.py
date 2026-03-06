import sys, os, asyncio, traceback
sys.path.insert(0, '/app')
os.chdir('/app')

async def main():
    try:
        from app.services.rag_service import rag_query
        r = await rag_query('que es el saber pro', 'Ingenieria de Sistemas')
        print('SUCCESS:', str(r)[:500])
    except Exception as e:
        print('ERROR:', type(e).__name__)
        traceback.print_exc()

asyncio.run(main())
