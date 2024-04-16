import json
import platform
import time
import asyncio

from src.socket_instance import emit_agent
from src.browser import Browser, start_interaction
from src.project import ProjectManager
from src.state import AgentState
from src.logger import Logger
from src.bert.sentence import SentenceBert
from src.memory import KnowledgeBase
from src.services import Netlify
from src.documenter.pdf import PDF
from src.filesystem import ReadCode
from src.browser.search import BingSearch, GoogleSearch, DuckDuckGoSearch
from src.planner import Planner
from src.researcher import Researcher
from src.formatter import Formatter
from src.coder import Coder
from src.action import Action
from src.internal_monologue import InternalMonologue
from src.answer import Answer
from src.runner import Runner
from src.feature import Feature
from src.patcher import Patcher
from src.reporter import Reporter
from src.decision import Decision
import tiktoken


class Agent:
    def __init__(self, base_model: str, search_engine: str, browser: Browser = None):
        if not base_model:
            raise ValueError("base_model is required")

        self.logger = Logger()

        self.collected_context_keywords = []
        self.planner = Planner(base_model=base_model)
        self.researcher = Researcher(base_model=base_model)
        self.formatter = Formatter(base_model=base_model)
        self.coder = Coder(base_model=base_model)
        self.action = Action(base_model=base_model)
        self.internal_monologue = InternalMonologue(base_model=base_model)
        self.answer = Answer(base_model=base_model)
        self.runner = Runner(base_model=base_model)
        self.feature = Feature(base_model=base_model)
        self.patcher = Patcher(base_model=base_model)
        self.reporter = Reporter(base_model=base_model)
        self.decision = Decision(base_model=base_model)

        self.project_manager = ProjectManager()
        self.agent_state = AgentState()
        self.engine = search_engine
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    async def open_page(self, project_name, pdf_download_url):
        browser = await Browser().start()
        await browser.go_to(pdf_download_url)
        _, raw = await browser.screenshot(project_name)
        data = await browser.extract_text()
        await browser.close()
        return browser, raw, data

    def search_queries(self, queries: list, project_name: str) -> dict:
        results = {}
        knowledge_base = KnowledgeBase()

        if self.engine == "bing":
            web_search = BingSearch()
        elif self.engine == "google":
            web_search = GoogleSearch()
        else:
            web_search = DuckDuckGoSearch()

        self.logger.info(f"Search Engine :: {self.engine}")

        for query in queries:
            query = query.strip().lower()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            web_search.search(query)
            link = web_search.get_first_link()
            self.logger.info(f"Link :: {link}")

            browser, raw, data = loop.run_until_complete(self.open_page(project_name, link))
            emit_agent("screenshot", {"data": raw, "project_name": project_name}, False)
            results[query] = self.formatter.execute(data, project_name)

            self.logger.info(f"Got search results for: {query}")

        return results

    def update_contextual_keywords(self, sentence: str):
        keywords = SentenceBert(sentence).extract_keywords()
        self.collected_context_keywords.extend(keyword[0] for keyword in keywords)
        return self.collected_context_keywords

    def make_decision(self, prompt: str, project_name: str) -> None:
        decision = self.decision.execute(prompt, project_name)

        for item in decision:
            function = item["function"]
            args = item["args"]
            reply = item["reply"]

            self.project_manager.add_message_from_devika(project_name, reply)

            if function == "git_clone":
                url = args["url"]
                # Implement git clone functionality here

            elif function == "generate_pdf_document":
                user_prompt = args["user_prompt"]
                markdown = self.reporter.execute([user_prompt], "", project_name)
                _out_pdf_file = PDF().markdown_to_pdf(markdown, project_name)
                self.project_manager.add_message_from_devika(project_name, f"PDF document generated.")

            elif function == "browser_interaction":
                user_prompt = args["user_prompt"]
                start_interaction(self.base_model, user_prompt, project_name)

            elif function == "coding_project":
                user_prompt = args["user_prompt"]
                plan = self.planner.execute(user_prompt, project_name)
                research = self.researcher.execute(plan, self.collected_context_keywords, project_name)
                search_results = self.search_queries(research["queries"], project_name)
                code = self.coder.execute(step_by_step_plan=plan,
                                          user_context=research["ask_user"],
                                          search_results=search_results,
                                          project_name=project_name)
                self.coder.save_code_to_project(code, project_name)

    def subsequent_execute(self, prompt: str, project_name: str) -> None:
        os_system = platform.platform()
        self.agent_state.set_agent_active(project_name, True)

        conversation = self.project_manager.get_all_messages_formatted(project_name)
        code_markdown = ReadCode(project_name).code_set_to_markdown()

        response, action = self.action.execute(conversation, project_name)
        self.project_manager.add_message_from_devika(project_name, response)

        if action == "answer":
            response = self.answer.execute(conversation=conversation,
                                           code_markdown=code_markdown,
                                           project_name=project_name)
            self.project_manager.add_message_from_devika(project_name, response)

        elif action == "run":
            project_path = self.project_manager.get_project_path(project_name)
            self.runner.execute(conversation=conversation,
                                code_markdown=code_markdown,
                                os_system=os_system,
                                project_path=project_path,
                                project_name=project_name)

        elif action == "deploy":
            deploy_metadata = Netlify().deploy(project_name)
            deploy_url = deploy_metadata["deploy_url"]
            response = {
                "message": "Done! I deployed your project on Netlify.",
                "deploy_url": deploy_url
            }
            self.project_manager.add_message_from_devika(project_name, json.dumps(response, indent=4))

        elif action == "feature":
            code = self.feature.execute(conversation=conversation,
                                        code_markdown=code_markdown,
                                        system_os=os_system,
                                        project_name=project_name)
            self.feature.save_code_to_project(code, project_name)

        elif action == "bug":
            code = self.patcher.execute(conversation=conversation,
                                        code_markdown=code_markdown,
                                        commands=None,
                                        error=prompt,
                                        system_os=os_system,
                                        project_name=project_name)
            self.patcher.save_code_to_project(code, project_name)

        elif action == "report":
            markdown = self.reporter.execute(conversation,
                                             code_markdown,
                                             project_name)
            _out_pdf_file = PDF().markdown_to_pdf(markdown, project_name)
            self.project_manager.add_message_from_devika(project_name, f"PDF document generated.")

        self.agent_state.set_agent_active(project_name, False)
        self.agent_state.set_agent_completed(project_name, True)
        self.project_manager.add_message_from_devika(project_name,
                                                     "Task completed. Let me know if you need anything else.")

    def execute(self, prompt: str, project_name_from_user: str = None) -> str:
        if project_name_from_user:
            self.project_manager.add_message_from_user(project_name_from_user, prompt)

        plan = self.planner.execute(prompt, project_name_from_user)
        planner_response = self.planner.parse_response(plan)

        if not project_name_from_user:
            project_name = planner_response["project"]
            self.project_manager.create_project(project_name)
            self.project_manager.add_message_from_user(project_name, prompt)
        else:
            project_name = project_name_from_user

        reply = planner_response["reply"]
        focus = planner_response["focus"]
        self.update_contextual_keywords(focus)

        internal_monologue = self.internal_monologue.execute(current_prompt=plan,
                                                             project_name=project_name)
        new_state = self.agent_state.new_state()
        new_state["internal_monologue"] = internal_monologue
        self.agent_state.add_to_current_state(project_name, new_state)

        research = self.researcher.execute(plan, self.collected_context_keywords,
                                           project_name=project_name)
        queries = research["queries"]
        queries_combined = ", ".join(queries) if queries else ""
        ask_user = research["ask_user"]

        if queries:
            self.project_manager.add_message_from_devika(project_name,
                                                         f"I am researching the queries: {queries_combined}. "
                                                         f"If I need anything, I'll ask you.")

        if ask_user:
            self.project_manager.add_message_from_devika(project_name, ask_user)

        search_results = self.search_queries(queries, project_name) if queries else {}
        code = self.coder.execute(step_by_step_plan=plan,
                                  user_context=ask_user,
                                  search_results=search_results,
                                  project_name=project_name)
        self.coder.save_code_to_project(code, project_name)

        self.agent_state.set_agent_completed(project_name, True)
        self.project_manager.add_message_from_devika(project_name,
                                                     "Task completed. Let me know if you need anything else.")

        return "Task completed. Let me know if you need anything else."
