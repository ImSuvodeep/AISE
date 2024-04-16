from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.llm import LLM

class Formatter:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)
        self.env = Environment(loader=FileSystemLoader("src/agents/formatter"), autoescape=select_autoescape())

    def render(self, raw_text: str) -> str:
        template = self.env.get_template("prompt.jinja2")
        return template.render(raw_text=raw_text)

    def validate_response(self, response: str) -> bool:
        # Implement actual response validation logic here
        # Example: Check if the response is valid JSON or meets certain criteria
        try:
            # Placeholder validation logic, replace with actual implementation
            return len(response.strip()) > 0
        except Exception:
            return False

    def execute(self, raw_text: str, project_name: str) -> str:
        try:
            rendered_text = self.render(raw_text)
            response = self.llm.inference(rendered_text, project_name)
            if self.validate_response(response):
                return response
            else:
                raise ValueError("Invalid response from the model")
        except Exception as e:
            # Handle any exceptions raised during execution
            print(f"Error executing Formatter: {e}")
            return ""
