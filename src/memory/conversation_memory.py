"""
AI 会话记忆管理 —— 会话、消息、持久化
"""

import json, logging
from datetime import datetime
from typing import Optional

from sqlalchemy import desc
from src.data.models_v6 import AISession, AIMessage

logger = logging.getLogger(__name__)


class ConversationMemory:
    """AI 会话记忆管理器"""

    def __init__(self):
        from src.utils.database import SessionLocal

        self.db = SessionLocal()
        self._current_session_id = None

    def close(self):
        try: self.db.close()
        except: pass

    def create_session(self, session_type: str = "free_chat",
                       title: str = "") -> int:
        session = AISession(session_type=session_type, title=title)
        self.db.add(session)
        self.db.commit()
        self._current_session_id = session.id
        return session.id

    def get_or_create_session(self, session_type: str = "free_chat") -> int:
        if self._current_session_id:
            return self._current_session_id
        return self.create_session(session_type=session_type)

    def update_title(self, session_id: int, title: str):
        row = self.db.query(AISession).filter(AISession.id == session_id).first()
        if row:
            row.title = title
            row.updated_at = datetime.now()
            self.db.commit()

    def save_message(self, session_id: int, role: str, content: str,
                     stock_code: str = None, structured_output: dict = None,
                     tools_used: list = None, **kwargs):
        msg = AIMessage(
            session_id=session_id, stock_code=stock_code,
            role=role, content=content,
            structured_output=structured_output,
            tools_used=tools_used,
            **kwargs,
        )
        self.db.add(msg)
        self.db.commit()
        return msg.id

    def get_session_messages(self, session_id: int, limit: int = 50) -> list:
        rows = (self.db.query(AIMessage)
                .filter(AIMessage.session_id == session_id)
                .order_by(AIMessage.created_at)
                .limit(limit).all())
        return [
            {"id": r.id, "role": r.role, "content": r.content,
             "stock_code": r.stock_code,
             "structured_output": r.structured_output,
             "tools_used": r.tools_used,
             "created_at": r.created_at.isoformat()}
            for r in rows
        ]

    def get_chat_history(self, session_id: int, limit: int = 20) -> list:
        msgs = self.get_session_messages(session_id, limit=limit * 2)
        history = []
        for m in msgs[-limit * 2:]:
            history.append({"role": m["role"], "content": m["content"]})
        return history

    def list_sessions(self, limit: int = 20) -> list:
        rows = (self.db.query(AISession)
                .order_by(desc(AISession.updated_at))
                .limit(limit).all())
        return [
            {"id": r.id, "type": r.session_type, "title": r.title,
             "updated_at": r.updated_at.isoformat()}
            for r in rows
        ]

    def list_recent_threads(self, limit: int = 20) -> list:
        """返回会话摘要，给移动端/AI页做历史入口。"""
        sessions = self.list_sessions(limit=limit)
        out = []
        for session in sessions:
            latest = (self.db.query(AIMessage)
                      .filter(AIMessage.session_id == session["id"])
                      .order_by(desc(AIMessage.created_at))
                      .first())
            out.append({
                **session,
                "last_role": latest.role if latest else "",
                "last_content": latest.content[:160] if latest else "",
                "stock_code": latest.stock_code if latest else None,
            })
        return out

    def get_stock_conversations(self, code: str, limit: int = 10) -> list:
        rows = (self.db.query(AIMessage)
                .filter(AIMessage.stock_code == code)
                .order_by(desc(AIMessage.created_at))
                .limit(limit).all())
        return [
            {"id": r.id, "session_id": r.session_id,
             "role": r.role, "content": r.content[:500],
             "structured_output": r.structured_output,
             "tools_used": r.tools_used,
             "created_at": r.created_at.isoformat()}
            for r in rows
        ]

    def search_messages(self, keyword: str, limit: int = 20) -> list:
        kw = f"%{keyword.strip()}%"
        rows = (self.db.query(AIMessage)
                .filter(AIMessage.content.like(kw))
                .order_by(desc(AIMessage.created_at))
                .limit(limit).all())
        return [
            {"id": r.id, "session_id": r.session_id,
             "role": r.role, "stock_code": r.stock_code,
             "content": r.content[:500],
             "structured_output": r.structured_output,
             "tools_used": r.tools_used,
             "created_at": r.created_at.isoformat()}
            for r in rows
        ]

    def get_recent_pairs(self, limit: int = 20) -> list:
        """把数据库消息还原为页面可展示的问答对。"""
        rows = (self.db.query(AIMessage)
                .order_by(desc(AIMessage.created_at), desc(AIMessage.id))
                .limit(limit * 4)
                .all())
        rows = list(reversed(rows))
        pairs = []
        last_user = None
        for row in rows:
            if row.role == "user":
                last_user = row
            elif row.role == "assistant" and last_user and last_user.session_id == row.session_id:
                pairs.append({
                    "question": last_user.content,
                    "answer": row.content,
                    "timestamp": row.created_at.isoformat(),
                    "tools_used": row.tools_used or [],
                    "stock_code": row.stock_code or last_user.stock_code,
                    "session_id": row.session_id,
                })
                last_user = None
        return pairs[-limit:]

    def import_legacy_history(self, items: list[dict], source: str = "legacy_json") -> int:
        """导入旧版 latest_conversation.json，保留旧聊天。"""
        imported = 0
        for item in items or []:
            question = str(item.get("question") or "").strip()
            answer = str(item.get("answer") or "").strip()
            if not question and not answer:
                continue
            if answer and self.db.query(AIMessage).filter(AIMessage.content == answer).first():
                continue
            stock_code = _extract_code(question + "\n" + answer)
            session_id = self.create_session("legacy_chat", title=(question or source)[:80])
            ts = _parse_time(item.get("timestamp"))
            if question:
                user_id = self.save_message(
                    session_id, "user", question, stock_code=stock_code or None,
                    tools_used=[],
                )
                if ts:
                    msg = self.db.query(AIMessage).filter(AIMessage.id == user_id).first()
                    msg.created_at = ts
            if answer:
                ai_id = self.save_message(
                    session_id, "assistant", answer, stock_code=stock_code or None,
                    tools_used=item.get("tools_used") or [],
                )
                if ts:
                    msg = self.db.query(AIMessage).filter(AIMessage.id == ai_id).first()
                    msg.created_at = ts
            imported += 1
        self.db.commit()
        return imported

    def save_to_json(self, filepath: str):
        sessions = []
        for s in self.list_sessions():
            msgs = self.get_session_messages(s["id"])
            sessions.append({**s, "messages": msgs})
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)


def _extract_code(text: str) -> str:
    import re

    m = re.search(r"\b(\d{6})\b", text or "")
    return m.group(1) if m else ""


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None
