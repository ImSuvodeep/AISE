import json
from jinja2 import Environment, BaseLoader
from typing import List, Union

from src.llm import LLM
from src.browser.search import BingSearch

# Load the Jinja2 template from file
with open("src/agents/researcher/prompt.jinja2", "r") as prompt_file:
    PROMPT = prompt_file.read().strip()

//if the BT us traversed in order, the order in which the node will be visited is 
class Researcher:
    def __init__(self, base_model: str):
        self.bing_search = BingSearch()
        self.llm = LLM(model_id=base_model)

    def render(self, step_by_step_plan: str, contextual_keywords: str) -> str:
        """Render the template with the given step-by-step plan and contextual keywords."""
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(
            step_by_step_plan=step_by_step_plan,
            contextual_keywords=contextual_keywords
        )

    def validate_response(self, response: str) -> Union[dict, bool]:
        """Validate and parse the model response."""
        response = response.strip().replace("```json", "```")
        if response.startswith("```") and response.endswith("```"):
            response = response[3:-3].strip()
        try:
            response_dict = json.loads(response)
        except Exception as e:
            print(f"Error parsing response JSON: {e}")
            return False

        if "queries" in response_dict and "ask_user" in response_dict:
            return {
                "queries": response_dict["queries"],
                "ask_user": response_dict["ask_user"]
            }
        else:
            return False

    def execute(self, step_by_step_plan: str, contextual_keywords: List[str], project_name: str) -> Union[dict, bool]:
        """Execute the research task with the given plan, keywords, and project name."""
        contextual_keywords_str = ", ".join(map(str.capitalize, contextual_keywords))
        prompt = self.render(step_by_step_plan, contextual_keywords_str)
        
        response = self.llm.inference(prompt, project_name)
        
        valid_response = self.validate_response(response)

        if not valid_response:
            print("Invalid response from the model, trying again...")
            return self.execute(step_by_step_plan, contextual_keywords, project_name)

        return valid_response
