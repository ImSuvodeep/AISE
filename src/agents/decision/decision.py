import json
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.llm import LLM

class Decision:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)
        self.env = Environment(loader=FileSystemLoader("src/agents/decision"), autoescape=select_autoescape())

    def render(self, prompt: str) -> str:
        template = self.env.get_template("prompt.jinja2")
        return template.render(prompt=prompt)

    def validate_response(self, response: str) -> bool:
        response = response.strip().replace("```json", "```")

        if response.startswith("```") and response.endswith("```"):
            response = response[3:-3].strip()

        try:
            data = json.loads(response)
            if not isinstance(data, list):
                return False

            for item in data:
                if not all(key in item for key in ["function", "args", "reply"]):
                    return False
        except json.JSONDecodeError:
            return False

        return True

    def execute(self, prompt: str, project_name: str) -> str:
        while True:
            rendered_prompt = self.render(prompt)
            response = self.llm.inference(rendered_prompt, project_name)

            if self.validate_response(response):
                return response
            else:
                print("Invalid response from the model, trying again...")
