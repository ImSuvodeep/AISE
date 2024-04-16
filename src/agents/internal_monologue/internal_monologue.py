import json
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.llm import LLM

class InternalMonologue:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)
        self.env = Environment(loader=FileSystemLoader("src/agents/internal_monologue"), autoescape=select_autoescape())

    def render(self, current_prompt: str) -> str:
        template = self.env.get_template("prompt.jinja2")
        return template.render(current_prompt=current_prompt)

    def validate_response(self, response: str) -> str:
        try:
            response = response.strip()
            if response.startswith("```") and response.endswith("```"):
                response = response[3:-3].strip()
            
            json_response = json.loads(response.replace("\\", ""))
            if "internal_monologue" in json_response:
                return json_response["internal_monologue"]
            else:
                return False
        except Exception as e:
            print(f"Error validating response: {e}")
            return False

    def execute(self, current_prompt: str, project_name: str) -> str:
        try:
            while True:
                rendered_prompt = self.render(current_prompt)
                response = self.llm.inference(rendered_prompt, project_name)
                valid_response = self.validate_response(response)
                if valid_response:
                    return valid_response
                else:
                    print("Invalid response from the model, trying again...")
        except Exception as e:
            print(f"Error executing InternalMonologue: {e}")
            return ""
