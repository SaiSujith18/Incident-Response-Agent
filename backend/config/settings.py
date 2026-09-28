import os

from dotenv import load_dotenv

load_dotenv()


HINDSIGHT_BASE_URL = os.getenv(
    "HINDSIGHT_BASE_URL",
    "https://api.hindsight.vectorize.io"
)

HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY")

HINDSIGHT_BANK_ID = os.getenv(
    "HINDSIGHT_BANK_ID",
    "memoryops-demo"
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)