from langchain_openai import ChatOpenAI as OpenAI
from src.config.config import config

# OpenAI Client
openai_client: OpenAI = OpenAI(api_key=config.OPENAI_API_KEY, model=config.OPENAI_MODEL)