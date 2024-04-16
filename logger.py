import os
import toml
from fastlogging import LogInit
from flask import Flask, request, jsonify

app = Flask(__name__)

class Config:
    def __init__(self):
        self.config_file = "config.toml"
        self.default_config_file = "sample.config.toml"
        self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_file):
            self._copy_default_config()
        try:
            with open(self.config_file, "r") as f:
                self.config = toml.load(f)
        except (OSError, toml.TomlDecodeError) as e:
            print(f"Error loading config file: {e}")
            self.config = {}

    def _copy_default_config(self):
        try:
            with open(self.default_config_file, "r") as src, open(self.config_file, "w") as dst:
                dst.write(src.read())
        except OSError as e:
            print(f"Error copying default config: {e}")

    def save_config(self):
        try:
            with open(self.config_file, "w") as f:
                toml.dump(self.config, f)
        except OSError as e:
            print(f"Error saving config file: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

class Logger:
    def __init__(self, filename="devika_agent.log"):
        self.config = Config()
        logs_dir = self.config.get("STORAGE.LOGS_DIR", "logs")  # Provide a default value
        log_file_path = os.path.join(logs_dir, filename)
        self.logger = LogInit(pathName=log_file_path, console=True, colors=True, encoding="utf-8")

    def log(self, level, message):
        log_method = getattr(self.logger, level)
        log_method(message)
        self.logger.flush()

def route_logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        log_enabled = Config().get("LOGGING.LOG_REST_API", False)

        # Log entry point
        if log_enabled:
            app.logger.info(f"{request.path} {request.method}")

        # Call the actual route function
        try:
            response = func(*args, **kwargs)
        except Exception as e:
            app.logger.error(f"Error in {request.path} {request.method}: {e}")
            response = jsonify({"error": str(e)}), 500

        # Log exit point
        if log_enabled:
            response_summary = response.get_data(as_text=True) if hasattr(response, "get_data") else str(response)
            app.logger.debug(f"{request.path} {request.method} - Response: {response_summary}")

        return response
    return wrapper

@app.route("/api/data", methods=["GET"])
@route_logger
def get_data():
    message = {"status": "success", "data": "some data"}
    return jsonify(message)

if __name__ == "__main__":
    app.run(debug=True)
