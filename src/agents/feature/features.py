import os
import time
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import List, Dict, Union
from src.config import Config
from src.llm import LLM
from src.state import AgentState

class Feature:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)
        self.project_dir = Config().get_projects_dir()
        self.env = Environment(loader=FileSystemLoader("src/agents/feature"), autoescape=select_autoescape())

    def render(self, conversation: List[str], code_markdown: str, system_os: str) -> str:
        template = self.env.get_template("prompt.jinja2")
        return template.render(conversation=conversation, code_markdown=code_markdown, system_os=system_os)

    def validate_response(self, response: str) -> Union[List[Dict[str, str]], bool]:
        try:
            response = response.strip()
            response = response.split("~~~", 1)[1]
            response = response[:response.rfind("~~~")]
            response = response.strip()
            data = json.loads(response)

            if not isinstance(data, list):
                return False

            result = []
            for item in data:
                if all(key in item for key in ["file", "code"]):
                    result.append(item)
                else:
                    return False

            return result
        except (json.JSONDecodeError, IndexError):
            return False

    def save_code_to_project(self, response: List[Dict[str, str]], project_name: str) -> str:
        project_path = os.path.join(self.project_dir, project_name.lower().replace(" ", "-"))
        os.makedirs(project_path, exist_ok=True)

        for file_data in response:
            file_path = os.path.join(project_path, file_data["file"])
            with open(file_path, "w") as f:
                f.write(file_data["code"])

        return project_path

    def response_to_markdown_prompt(self, response: List[Dict[str, str]]) -> str:
        formatted_files = [f"File: `{file['file']}`:\n```\n{file['code']}\n```" for file in response]
        return f"~~~\n{'\n'.join(formatted_files)}\n~~~"

    def emulate_code_writing(self, code_set: List[Dict[str, str]], project_name: str):
        current_state = AgentState().get_latest_state(project_name)
        for file_data in code_set:
            filename = file_data["file"]
            code = file_data["code"]

            new_state = AgentState().new_state()
            new_state["internal_monologue"] = "Writing code..."
            new_state["terminal_session"]["title"] = f"Editing {filename}"
            new_state["terminal_session"]["command"] = f"vim {filename}"
            new_state["terminal_session"]["output"] = code

            AgentState().add_to_current_state(project_name, new_state)
            time.sleep(1)

    def execute(self, conversation: List[str], code_markdown: str, system_os: str, project_name: str) -> str:
        while True:
            prompt = self.render(conversation, code_markdown, system_os)
            response = self.llm.inference(prompt, project_name)
        
            valid_response = self.validate_response(response)
        
            if valid_response:
                self.emulate_code_writing(valid_response, project_name)
                return valid_response
            else:
                print("Invalid response from the model, trying again...")
