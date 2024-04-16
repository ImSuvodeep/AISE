import json
from datetime import datetime
from typing import Optional
from sqlmodel import Field, Session, SQLModel, create_engine
from src.socket_instance import emit_agent
from src.config import Config
from src.logger import Logger

class AgentStateModel(SQLModel, table=True):
    __tablename__ = "agent_state"

    id: Optional[int] = Field(default=None, primary_key=True)
    project: str
    state_stack_json: str


class AgentState:
    def __init__(self):
        self.config = Config()
        sqlite_path = self.config.get_sqlite_db()
        self.engine = create_engine(f"sqlite:///{sqlite_path}")
        SQLModel.metadata.create_all(self.engine)
        self.logger = Logger()

    def new_state(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "internal_monologue": None,
            "browser_session": {
                "url": None,
                "screenshot": None
            },
            "terminal_session": {
                "command": None,
                "output": None,
                "title": None
            },
            "step": None,
            "message": None,
            "completed": False,
            "agent_is_active": True,
            "token_usage": 0,
            "timestamp": timestamp
        }

    def _get_session(self) -> Session:
        return Session(self.engine)

    def _get_agent_state(self, session: Session, project: str) -> Optional[AgentStateModel]:
        return session.query(AgentStateModel).filter(AgentStateModel.project == project).first()

    def _update_agent_state(self, session: Session, agent_state: AgentStateModel, state_stack: list):
        agent_state.state_stack_json = json.dumps(state_stack)
        session.commit()

    def _emit_agent_state(self, state_stack: list):
        emit_agent("agent-state", state_stack)

    def _get_latest_state(self, state_stack: list) -> Optional[dict]:
        if state_stack:
            return state_stack[-1]
        return None

    def add_to_current_state(self, project: str, state: dict):
        with self._get_session() as session:
            agent_state = self._get_agent_state(session, project)
            state_stack = json.loads(agent_state.state_stack_json) if agent_state else []
            state_stack.append(state)
            
            if agent_state:
                self._update_agent_state(session, agent_state, state_stack)
            else:
                agent_state = AgentStateModel(project=project, state_stack_json=json.dumps(state_stack))
                session.add(agent_state)
                session.commit()
            
            self._emit_agent_state(state_stack)

    def get_current_state(self, project: str) -> Optional[list]:
        with self._get_session() as session:
            agent_state = self._get_agent_state(session, project)
            if agent_state:
                return json.loads(agent_state.state_stack_json)
            return None

    def update_latest_state(self, project: str, state: dict):
        with self._get_session() as session:
            agent_state = self._get_agent_state(session, project)
            if agent_state:
                state_stack = json.loads(agent_state.state_stack_json)
                state_stack[-1] = state
                self._update_agent_state(session, agent_state, state_stack)
            else:
                state_stack = [state]
                agent_state = AgentStateModel(project=project, state_stack_json=json.dumps(state_stack))
                session.add(agent_state)
                session.commit()
            self._emit_agent_state(state_stack)
            

    def set_agent_active(self, project: str, is_active: bool):
        with self._get_session() as session:
            agent_state = self._get_agent_state(session, project)
            if agent_state:
                state_stack = json.loads(agent_state.state_stack_json)
                state_stack[-1]["agent_is_active"] = is_active
                self._update_agent_state(session, agent_state, state_stack)
            else:
                state_stack = [self.new_state()]
                state_stack[-1]["agent_is_active"] = is_active
                agent_state = AgentStateModel(project=project, state_stack_json=json.dumps(state_stack))
                session.add(agent_state)
                session.commit()
            self._emit_agent_state(state_stack)

    def is_agent_active(self, project: str) -> Optional[bool]:
        with self._get_session() as session:
            agent_state = self._get_agent_state(session, project)
            if agent_state:
                return json.loads(agent_state.state_stack_json)[-1]["agent_is_active"]
            return None

    def set_agent_completed(self, project: str, is_completed: bool):
        with self._get_session() as session:
            agent_state = self._get_agent_state(session, project)
            if agent_state:
                state_stack = json.loads(agent_state.state_stack_json)
                state_stack[-1]["internal_monologue"] = "Agent has completed the task."
                state_stack[-1]["completed"] = is_completed
                self._update_agent_state(session, agent_state, state_stack)
            else:
                state_stack = [self.new_state()]
                state_stack[-1]["completed"] = is_completed
                agent_state = AgentStateModel(project=project, state_stack_json=json.dumps(state_stack))
                session.add(agent_state)
                session.commit()
            self._emit_agent_state(state_stack)

    def is_agent_completed(self, project: str) -> Optional[bool]:
        with self._get_session() as session:
            agent_state = self._get_agent_state(session, project)
            if agent_state:
                return json.loads(agent_state.state_stack_json)[-1]["completed"]
            return None

    def update_token_usage(self, project: str, token_usage: int):
        with self._get_session() as session:
            agent_state = self._get_agent_state(session, project)
            if agent_state:
                state_stack = json.loads(agent_state.state_stack_json)
                state_stack[-1]["token_usage"] += token_usage
                self._update_agent_state(session, agent_state, state_stack)
            else:
                state_stack = [self.new_state()]
                state_stack[-1]["token_usage"] = token_usage
                agent_state = AgentStateModel(project=project, state_stack_json=json.dumps(state_stack))
                session.add(agent_state)
                session.commit()

    def get_latest_token_usage(self, project: str) -> int:
        with self._get_session() as session:
            agent_state = self._get_agent_state(session, project)
            if agent_state:
                return json.loads(agent_state.state_stack_json)[-1]["token_usage"]
            return 0
