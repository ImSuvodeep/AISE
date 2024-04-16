import os
import time
from jinja2 import Environment, FileSystemLoader
from typing import List, Dict, Union
from src.config import Config
from src.llm import LLM
from src.state import AgentState
from src.logger import Logger

class Coder:
    def __init__(self, base_model: str):
        self.config = Config()
        self.project_dir = self.config.get_projects_dir()
        self.logger = Logger()
        self.llm = LLM(model_id=base_model)
        self.env = Environment(loader=FileSystemLoader("src/agents/coder"))

    def render(self, step_by_step_plan: str, user_context: str, search_results: dict) -> str:
        template = self.env.get_template("prompt.jinja2")
        return template.render(
            step_by_step_plan=step_by_step_plan,
            user_context=user_context,
            search_results=search_results,
        )

    def validate_response(self, response: str) -> Union[List[Dict[str, str]], bool]:
        response = response.strip()

        self.logger.debug(f"Response from the model: {response}")

        if "~~~" not in response:
            return False

        response = response.split("~~~", 1)[1]
        response = response[:response.rfind("~~~")]
        response = response.strip()

        result = []
        current_file = None
        current_code = []
        code_block = False

        for line in response.split("\n"):
            if line.startswith("File: "):
                if current_file and current_code:
                    result.append({"file": current_file, "code": "\n".join(current_code)})
                current_file = line.split("`")[1].strip()
                current_code = []
                code_block = False
            elif line.startswith("```"):
                code_block = not code_block
            elif not code_block and current_file:
                current_code.append(line)

        if current_file and current_code:
            result.append({"file": current_file, "code": "\n".join(current_code)})

        return result if result else False

    def save_code_to_project(self, response: List[Dict[str, str]], project_name: str) -> str:
        project_path = os.path.join(self.project_dir, project_name.lower().replace(" ", "-"))
        os.makedirs(project_path, exist_ok=True)

        for file_data in response:
            file_path = os.path.join(project_path, file_data["file"])
            with open(file_path, "w") as f:
                f.write(file_data["code"])

        return project_path

    def emulate_code_writing(self, code_set: List[Dict[str, str]], project_name: str):
        current_state = AgentState().get_latest_state(project_name)

        for file_data in code_set:
            file_name = file_data["file"]
            code_content = file_data["code"]

            new_state = AgentState().new_state()
            new_state["browser_session"] = current_state["browser_session"]
            new_state["internal_monologue"] = "Writing code..."
            new_state["terminal_session"]["title"] = f"Editing {file_name}"
            new_state["terminal_session"]["command"] = f"vim {file_name}"
            new_state["terminal_session"]["output"] = code_content

            AgentState().add_to_current_state(project_name, new_state)
            time.sleep(2)

    def execute(self, step_by_step_plan: str, user_context: str, search_results: dict, project_name: str) -> str:
        while True:
            prompt = self.render(step_by_step_plan, user_context, search_results)
            response = self.llm.inference(prompt, project_name)
            valid_response = self.validate_response(response)

            if valid_response:
                self.emulate_code_writing(valid_response, project_name)
                return valid_response

            print("Invalid response from the model, trying again...")
