"""用户个性化记忆 —— 偏好/风格/常看股票"""

import json, logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
PROFILE_FILE = Path(__file__).parent.parent.parent / "data" / "user_profile.json"


class UserProfile:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        try:
            if PROFILE_FILE.exists():
                return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        except Exception: pass
        return {"preferences": {}, "top_stocks": [], "top_sectors": [],
                "trading_style": "", "stats": {"chats": 0, "analyses": 0, "compares": 0},
                "created_at": datetime.now().isoformat()}

    def save(self):
        try:
            PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
            PROFILE_FILE.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e: logger.warning(f"save profile: {e}")

    def set(self, key, val):
        self.data["preferences"][key] = val; self.save()

    def get(self, key, d=""):
        return self.data["preferences"].get(key, d)

    def track_stock(self, code, name=""):
        stocks = self.data["top_stocks"]
        for s in stocks:
            if s[0] == code: s[2] += 1; self.save(); return
        stocks.append([code, name, 1])
        if len(stocks) > 20:
            stocks.sort(key=lambda x: x[2], reverse=True)
            stocks[:] = stocks[:20]
        self.save()

    def top_stocks(self, n=5):
        return sorted(self.data["top_stocks"], key=lambda x: x[2], reverse=True)[:n]

    def track_sector(self, s):
        if s not in self.data["top_sectors"]:
            self.data["top_sectors"].append(s)
            if len(self.data["top_sectors"]) > 10:
                self.data["top_sectors"] = self.data["top_sectors"][-10:]
            self.save()

    def record_chat(self):
        self.data["stats"]["chats"] += 1; self.save()

    def record_analysis(self):
        self.data["stats"]["analyses"] += 1; self.save()

    def record_compare(self):
        self.data["stats"]["compares"] += 1; self.save()

    def build_context(self):
        """生成 AI 上下文"""
        lines = ["[用户画像]"]
        for k, v in self.data.get("preferences", {}).items():
            lines.append(f"- {k}: {v}")
        top = self.top_stocks(5)
        if top:
            lines.append("- 常看: " + ", ".join(f"{n}({c})" for c, n, _ in top))
        if self.data.get("trading_style"):
            lines.append(f"- 风格: {self.data['trading_style']}")
        s = self.data.get("stats", {})
        if s:
            lines.append(f"- 累计: {s.get('chats',0)}次对话 {s.get('analyses',0)}次分析 {s.get('compares',0)}次对比")
        return "\n".join(lines) if len(lines) > 1 else ""


_profile = None


def get_profile() -> UserProfile:
    global _profile
    if _profile is None: _profile = UserProfile()
    return _profile
