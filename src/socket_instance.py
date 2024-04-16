import os
import json
import zipfile
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, select
from src.socket_instance import emit_agent
from src.config import Config
from sqlmodel import SQLModel, Field, Relationship


class Projects(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project: str
    message_stack_json: str


class ProjectManager:
    def __init__(self):
        self.config = Config()
        sqlite_path = self.config.get("STORAGE.SQLITE_DB")
        self.project_path = self.config.get("STORAGE.PROJECTS_DIR")
        self.engine = create_engine(f"sqlite:///{sqlite_path}")
        SQLModel.metadata.create_all(self.engine)

    def new_message(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "from_devika": True,
            "message": None,
            "timestamp": timestamp
        }

    def create_project(self, project: str):
        with Session(self.engine) as session:
            project_state = Projects(project=project, message_stack_json=json.dumps([]))
            session.add(project_state)
            session.commit()

    def _get_project(self, session: Session, project: str) -> Optional[Projects]:
        return session.exec(select(Projects).where(Projects.project == project)).first()

    def _update_message_stack(self, session: Session, project_state: Projects, message_stack: list):
        project_state.message_stack_json = json.dumps(message_stack)
        session.add(project_state)
        session.commit()

    def add_message_to_project(self, project: str, message: dict):
        with Session(self.engine) as session:
            project_state = self._get_project(session, project)
            if project_state:
                message_stack = json.loads(project_state.message_stack_json)
                message_stack.append(message)
            else:
                message_stack = [message]
                project_state = Projects(project=project, message_stack_json=json.dumps(message_stack))
            self._update_message_stack(session, project_state, message_stack)

    def add_message_from_devika(self, project: str, message: str):
        new_message = self.new_message()
        new_message["message"] = message
        emit_agent("server-message", {"messages": new_message})
        self.add_message_to_project(project, new_message)

    def add_message_from_user(self, project: str, message: str):
        new_message = self.new_message()
        new_message["message"] = message
        new_message["from_devika"] = False
        emit_agent("server-message", {"messages": new_message})
        self.add_message_to_project(project, new_message)

    def get_messages(self, project: str) -> Optional[list]:
        with Session(self.engine) as session:
            project_state = self._get_project(session, project)
            if project_state:
                return json.loads(project_state.message_stack_json)
            return None

    def get_project_list(self) -> list:
        with Session(self.engine) as session:
            projects = session.exec(select(Projects)).all()
            return [project.project for project in projects]

    def get_all_messages_formatted(self, project: str) -> list:
        formatted_messages = []
        with Session(self.engine) as session:
            project_state = self._get_project(session, project)
            if project_state:
                message_stack = json.loads(project_state.message_stack_json)
                for message in message_stack:
                    formatted_messages.append(f"Devika: {message['message']}" if message['from_devika']
                                              else f"User: {message['message']}")
            return formatted_messages

    def get_project_path(self, project: str) -> str:
        return os.path.join(self.project_path, project.lower().replace(" ", "-"))

    def project_to_zip(self, project: str) -> Optional[str]:
        project_path = self.get_project_path(project)
        zip_path = f"{project_path}.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    relative_path = os.path.relpath(os.path.join(root, file), os.path.join(project_path, '..'))
                    zipf.write(os.path.join(root, file), arcname=relative_path)

        return zip_path if os.path.exists(zip_path) else None

    def get_zip_path(self, project: str) -> str:
        return f"{self.get_project_path(project)}.zip"
