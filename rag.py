import os
import json

from openai import AsyncOpenAI, OpenAI
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from langchain_chroma import Chroma
import chromadb
from dotenv import load_dotenv
from typing import AsyncGenerator


class Rag:
    def __init__(self):
        
        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.settings = {
            "model": "deepseek-chat",
            "temperature": 0.3,
            "max_tokens": 1000,
            "top_p": 0.95,
            "stream": True
        }
        self.docs = None
        self.embedding = None
        self.db = None
        # Document types supported
        self.DOCUMENT_TYPES = {
            "иргэний үнэмлэхний лавалгаа": "civil_certificate",
            "оршин суугаа газрын тодорхойлолт": "residence_certificate", 
            "төрсний гэрчилгээ": "birth_certificate"
        }
        self.message_history = [{"role": "system", "content": "Чи бол ухаалаг туслах."}]
    
    def setup(self):
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "data/files", "main.txt")
        persistent_db = os.path.join(current_dir, "data/db", "chroma_db")

        # Ensure the text file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"The file {file_path} does not exist. Please chech the path"
            )
        
            # Read the text content from the file
        loader = TextLoader(file_path)
        documents = loader.load()

        # Split the document into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,       # Smaller chunks for agglutinative languages
            chunk_overlap=50,     # Overlap to preserve context
            separators=["\n\n", "\n", "。", " ", ""]  # Mongolian-specific separators
        )
        self.docs = text_splitter.split_documents(documents)

        #Display information about the split document
        print("\n--- Document chunk Information ---")
        print(f"Number of document chunks {len(self.docs)}")
        print(f"Sample chunk:\n{self.docs[0].page_content}\n")


        self.embeddings = HuggingFaceEmbeddings(
            model_name="intfloat/multilingual-e5-large",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}  # Crucial for accuracy
        )
        print("\n--- Finished creating Embedding ---")

        if not os.path.exists(persistent_db):
            print("Persistant directory does not exist. Initializing vector store...")

            
            
            # Create the vector store and persist it automatically

            print("\n --- Creating vector store ---") 
            self.db = Chroma.from_documents(
                documents=self.docs,
                embedding=self.embeddings,
                persist_directory=persistent_db,
                client_settings=chromadb.config.Settings(
                    anonymized_telemetry=False,
                    is_persistent=True
                )
            )

            print("\n--- Finished creating vector store ---")
        else:
            # Create the vector store and persist it automatically
            
            print("Persistant directory exist...")
            self.db = Chroma(
                persist_directory=persistent_db,
                embedding_function=self.embeddings,
                client_settings=chromadb.config.Settings(
                    anonymized_telemetry=False,
                    is_persistent=True
                )
            )
    
    async def retriever(self, query: str, voice=False)-> AsyncGenerator[str, None]:
        print(query)
        vector_retriever = self.db.as_retriever(search_kwargs={"k": 3})
        # Lexical retriever (BM25)
        bm25_retriever = BM25Retriever.from_documents(self.docs)
        bm25_retriever.k = 3

        # Ensemble both
        ensemble_retriever = EnsembleRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            weights=[0.6, 0.4]  # Tune based on your tests
        )
        relevant_docs = ensemble_retriever.invoke(query)
        
        combined_input = (
            "Дараах мэдээллээр асуултанд хариулна уу:"
            + "\n1. Хэрэв мэдээлэл хангалттай бол монгол хэлээр товч, ойлгомжтой хариул."
            + "\n2. Хэрэв мэдээлэл байхгүй бол 'Мэдэхгүй байна' гэж хариул."
            + "\n\n Контекст: ".join([doc.page_content for doc in relevant_docs])
            + f"\n\n Асуулт: {query}"
        )
        accumulated = ""
        try:
            # Get the completion response
            response = await self.client.chat.completions.create(
                messages=[*self.message_history, {"role": "user", "content": combined_input}],
                **self.settings
            )
            async for chunk in response:
                if token := chunk.choices[0].delta.content or "":
                    if not accumulated.endswith(token):
                        accumulated += token
                        # 4) yield just the new bit, so your SSE client/appends get only
                        #    what was added this round
                        yield token

        except Exception as e:
            print(f"Error getting response: {str(e)}")
            text_content = f"Error getting response: {str(e)}"

        self.message_history.append({"role": "assistant", "content": accumulated})    