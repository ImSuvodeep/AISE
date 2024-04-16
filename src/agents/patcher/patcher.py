import os
import time
from jinja2 import Environment, BaseLoader
from typing import List, Dict, Union
from src.config import Config
from src.llm import LLM
from src.state import AgentState

class Patcher:
    def __init__(self, base_model: str):
        self.project_dir = Config().get_projects_dir()
        self.llm = LLM(model_id=base_model)
        self.env = Environment(loader=BaseLoader())
        self.prompt_template = self.env.from_string(open("src/agents/patcher/prompt.jinja2").read().strip())

    def render(
        self,
        conversation: list,
        code_markdown: str,
        commands: list,
        error: str,
        system_os: str
    ) -> str:
        return self.prompt_template.render(
            conversation=conversation,
            code_markdown=code_markdown,
            commands=commands,
            error=error,
            system_os=system_os
        )

    def validate_response(self, response: str) -> Union[List[Dict[str, str]], bool]:
        try:
            response = response.strip()
            if "~~~" in response:
                response = response.split("~~~", 1)[1].rsplit("~~~", 1)[0].strip()
                result = []
                current_file = None
                current_code = []

                for line in response.split("\n"):
                    if line.startswith("File: "):
                        if current_file and current_code:
                            result.append({"file": current_file, "code": "\n".join(current_code)})
                        current_file = line.split("`")[1].strip()
                        current_code = []
                    elif not line.startswith("```"):
                        current_code.append(line)

                if current_file and current_code:
                    result.append({"file": current_file, "code": "\n".join(current_code)})
                return result
            else:
                return False
        except Exception as e:
            print(f"Error validating response: {e}")
            return False

    def save_code_to_project(self, response: List[Dict[str, str]], project_name: str) -> str:
        project_name = project_name.lower().replace(" ", "-")
        file_path_dir = f"{self.project_dir}/{project_name}"

        for file in response:
            file_path = f"{file_path_dir}/{file['file']}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(file["code"])

        return file_path_dir

    def response_to_markdown_prompt(self, response: List[Dict[str, str]]) -> str:
        return "\n".join([f"File: `{file['file']}`:\n```\n{file['code']}\n```" for file in response])

    def emulate_code_writing(self, code_set: list, project_name: str) -> None:
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

    def execute(
        self,
        conversation: list,
        code_markdown: str,
        commands: list,
        error: str,
        system_os: dict,
        project_name: str
    ) -> Union[List[Dict[str, str]], bool]:
        prompt = self.render(conversation, code_markdown, commands, error, system_os)
        response = self.llm.inference(prompt, project_name)
        
        valid_response = self.validate_response(response)
        
        while not valid_response:
            print("Invalid response from the model, trying again...")
            response = self.llm.inference(prompt, project_name)
            valid_response = self.validate_response(response)
        
        self.emulate_code_writing(valid_response, project_name)

        return valid_response
