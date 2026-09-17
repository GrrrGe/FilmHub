# # storage/session_service.py
# import logging
# from typing import Optional, Dict, List

# from google.adk.sessions import Session
# from google.adk.sessions.base_session_service import BaseSessionService
# from .state_schema import UserProfile

# _STORE: Dict[str, Session] = {}

# class PersistentSessionService(BaseSessionService):
#     """Manages user sessions, ensuring each has a UserProfile."""

#     # --- CHANGE: All methods are now 'async def' ---

#     async def get_session(self, app_name: str, user_id: str, session_id: str) -> Optional[Session]:
#         key = f"{user_id}:{session_id}"
#         if key in _STORE:
#             logging.info(f"SESSION: Retrieved session for key {key}")
#             return _STORE.get(key)
#         return None

#     async def create_session(self, app_name: str, user_id: str, session_id: str, state: Optional[dict] = None) -> Session:
#         key = f"{user_id}:{session_id}"
#         if key not in _STORE:
#             logging.info(f"SESSION: Creating new session for key {key}")
#             initial_state = {"user_profile": UserProfile()}
#             _STORE[key] = Session(
#                 app_name=app_name,
#                 user_id=user_id,
#                 id=session_id,
#                 state=initial_state
#             )
#         return _STORE[key]

#     async def update_session(self, session: Session) -> Session:
#         key = f"{session.user_id}:{session.id}"
#         logging.info(f"SESSION: Updating session for key {key}")
#         _STORE[key] = session
#         return session

#     async def delete_session(self, app_name: str, user_id: str, session_id: str) -> None:
#         key = f"{user_id}:{session_id}"
#         if key in _STORE:
#             logging.info(f"SESSION: Deleting session for key {key}")
#             del _STORE[key]

#     async def list_sessions(self, app_name: str, user_id: str) -> List[Session]:
#         user_sessions = []
#         for session in _STORE.values():
#             if session.user_id == user_id and session.app_name == app_name:
#                 user_sessions.append(session)
#         logging.info(f"SESSION: Found {len(user_sessions)} sessions for user {user_id}")
#         return user_sessions


import logging
from typing import Optional, Dict, List

from google.adk.sessions import Session
from google.adk.sessions.base_session_service import BaseSessionService
from .state_schema import UserProfile

_STORE: Dict[str, Session] = {}

class PersistentSessionService(BaseSessionService):
    """Manages user sessions, ensuring each has a UserProfile."""

    async def get_session(self, app_name: str, user_id: str, session_id: str) -> Optional[Session]:
        key = f"{user_id}:{session_id}"
        if key in _STORE:
            logging.info(f"SESSION: Retrieved session for key {key}")
            return _STORE.get(key)
        return None

    async def create_session(self, app_name: str, user_id: str, session_id: str, state: Optional[dict] = None) -> Session:
        key = f"{user_id}:{session_id}"
        if key not in _STORE:
            logging.info(f"SESSION: Creating new session for key {key}")
            initial_state = {"user_profile": UserProfile()}
            _STORE[key] = Session(
                app_name=app_name,
                user_id=user_id,
                id=session_id,
                state=initial_state
            )
        return _STORE[key]

    async def update_session(self, session: Session) -> Session:
        key = f"{session.user_id}:{session.id}"
        logging.info(f"SESSION: Updating session for key {key}")
        _STORE[key] = session
        return session

    async def delete_session(self, app_name: str, user_id: str, session_id: str) -> None:
        """Deletes a session from the in-memory store."""
        key = f"{user_id}:{session_id}"
        if key in _STORE:
            logging.info(f"SESSION: Deleting session for key {key}")
            del _STORE[key]

    async def list_sessions(self, app_name: str, user_id: str) -> List[Session]:
        """Lists all sessions for a given user from the in-memory store."""
        user_sessions = []
        for session in _STORE.values():
            if session.user_id == user_id and session.app_name == app_name:
                user_sessions.append(session)
        logging.info(f"SESSION: Found {len(user_sessions)} sessions for user {user_id}")
        return user_sessions
