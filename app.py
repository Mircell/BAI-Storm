import logging
import traceback
from flask import Flask, jsonify

from config import Config, setup_logging
from routes.main import main_bp

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Register blueprint
app.register_blueprint(main_bp)

# Global error handler to catch all unhandled exceptions and return JSON
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {traceback.format_exc()}")
    return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)