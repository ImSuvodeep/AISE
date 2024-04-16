import os
from src.config import Config
from src.logger import Logger
from src.bert.sentence import SentenceBert  # Assuming this import is required


def init_devika():
    config = Config()
    logger = Logger()

    try:
        logger.info("Initializing Devika...")

        # Retrieve necessary paths from configuration
        sqlite_db = config.get_sqlite_db()
        screenshots_dir = config.get_screenshots_dir()
        pdfs_dir = config.get_pdfs_dir()
        projects_dir = config.get_projects_dir()
        logs_dir = config.get_logs_dir()

        # Ensure required directories exist
        for directory in [os.path.dirname(sqlite_db), screenshots_dir, pdfs_dir, projects_dir, logs_dir]:
            os.makedirs(directory, exist_ok=True)

        logger.info("Prerequisite directories initialized.")

        # Load sentence-transformer BERT models
        logger.info("Loading sentence-transformer BERT models...")
        prompt = "Light-weight keyword extraction exercise for BERT model loading.".strip()
        SentenceBert(prompt).extract_keywords()
        logger.info("BERT model loaded successfully.")

    except Exception as e:
        logger.error(f"Error occurred during Devika initialization: {e}")

if __name__ == "__main__":
    init_devika()
