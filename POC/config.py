import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
USDA_API_KEY = os.getenv("USDA_API_KEY", "gZJUqbshltC7qfQ9lk0meZcMJjazosPLfPVnEbgF")

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

INSTACART_DIR = Path.home() / ".cache/kagglehub/datasets/yasserh/instacart-online-grocery-basket-analysis-dataset/versions/1"

# LLM Config
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_RPM_LIMIT = 25  # stay under 30 free tier limit

# OFF API
OFF_HEADERS = {"User-Agent": "DAMG7245-BigData/1.0 - academic project"}

# Demo scale
OFF_PRODUCT_COUNT = 50
USDA_PRODUCT_COUNT = 50
FDA_RECALL_COUNT = 100
OPEN_PRICES_COUNT = 100
ESCI_SAMPLE_COUNT = 500
INSTACART_ORDER_SAMPLE = 10000
