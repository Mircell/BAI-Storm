import logging
import os

class Config:
    SECRET_KEY = os.urandom(24)
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )