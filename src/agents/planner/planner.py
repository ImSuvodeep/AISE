import os
from jinja2 import Environment, FileSystemLoader
from src.llm import LLM

class Planner:
    def __init__(self, base_model: str, template_path: str):
        self.llm = LLM(model_id=base_model)
        self.env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
        self.template = self.env.get_template(os.path.basename(template_path))

    def render(self, prompt: str) -> str:
        return self.template.render(prompt=prompt)

    def validate_response(self, response: str) -> bool:
        # Placeholder validation logic
        return True

    def parse_response(self, response: str) -> dict:
        result = {
            "project": "",
            "reply": "",
            "focus": "",
            "plans": {},
            "summary": ""
        }

        current_section = None
        current_step = None

        for line in response.split("\n"):
            line = line.strip()

            if line.startswith("Project Name:"):
                current_section = "project"
                result["project"] = line.split(":", 1)[1].strip()
            elif line.startswith("Your Reply to the Human Prompter:"):
                current_section = "reply"
                result["reply"] = line.split(":", 1)[1].strip()
            elif line.startswith("Current Focus:"):
                current_section = "focus"
                result["focus"] = line.split(":", 1)[1].strip()
            elif line.startswith("Plan:"):
                current_section = "plans"
            elif line.startswith("Summary:"):
                current_section = "summary"
                result["summary"] = line.split(":", 1)[1].strip()
            elif current_section == "reply" or current_section == "focus" or current_section == "plans":
                if current_section == "reply":
                    result["reply"] += " " + line
                elif current_section == "focus":
                    result["focus"] += " " + line
                elif line.startswith("- [ ] Step"):
                    current_step = line.split(":")[0].strip().split(" ")[-1]
                    result["plans"][int(current_step)] = line.split(":", 1)[1].strip()
                elif current_step:
                    result["plans"][int(current_step)] += " " + line
            elif current_section == "summary":
                result["summary"] += " " + line.replace("```", "")

        result["project"] = result["project"].strip()
        result["reply"] = result["reply"].strip()
        result["focus"] = result["focus"].strip()
        result["summary"] = result["summary"].strip()

        return result

    def execute(self, prompt: str, project_name: str) -> dict:
        prompt = self.render(prompt)
        response = self.llm.inference(prompt, project_name)

        if not self.validate_response(response):
            raise ValueError("Invalid response from the model")

        return self.parse_response(response)
