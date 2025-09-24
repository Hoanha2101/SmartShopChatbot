from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv

for key in list(os.environ.keys()):
    os.environ.pop(key, None)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small",
                                    api_key = OPENAI_API_KEY)
