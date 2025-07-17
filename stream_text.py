import asyncio
from rag import Rag

async def test_rag():
    RAG = Rag()
    RAG.setup()
    async for raw_line in RAG.retriever(query="Даланзадгад сумын засаг дарга хэн бэ ?"):
        token = raw_line
        print(token, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(test_rag())

