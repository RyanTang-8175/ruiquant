"""
Phase 3.2: AlphaEye 推送通知系统
渠道优先级: 邮件(SMTP) > 企业微信 Webhook > iOS推送(后续)

配置从 data/settings.json 读取（不进git）:
  smtp_host / smtp_port / smtp_user / smtp_password / smtp_to
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
from typing import Optional

from src.config import get_setting

logger = logging.getLogger(__name__)


def _smtp_config() -> dict:
    return {
        "host": get_setting("smtp_host", "SMTP_HOST", ""),
        "port": int(get_setting("smtp_port", "SMTP_PORT", "587") or 587),
        "user": get_setting("smtp_user", "SMTP_USER", ""),
        "password": get_setting("smtp_password", "SMTP_PASSWORD", ""),
        "to": get_setting("smtp_to", "SMTP_TO", ""),
    }


def is_configured() -> bool:
    cfg = _smtp_config()
    return bool(cfg["host"] and cfg["user"] and cfg["password"] and cfg["to"])


def send_email(subject: str, body_html: str, to: Optional[str] = None) -> bool:
    """SMTP 发送邮件。Returns True if sent successfully."""
    cfg = _smtp_config()
    if not cfg["host"]:
        logger.warning("SMTP 未配置，跳过邮件发送")
        return False
    recipient = to or cfg["to"]
    if not recipient:
        logger.warning("SMTP 收件人未配置")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg["user"]
        msg["To"] = recipient
        msg.attach(MIMEText(body_html, "html", "utf-8"))
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], [recipient], msg.as_string())
        logger.info(f"邮件已发送: {subject}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False


def morning_push() -> bool:
    """盘前计划推送（08:27 触发）"""
    today = date.today()
    wday = ["周一","周二","周三","周四","周五","周六","周日"][today.weekday()]
    try:
        from src.data.realtime import get_market_overview
        ov = get_market_overview()
        indices = ov.get("indices", [])
        idx_text = " | ".join(
            f"{i.get('name','')} {i.get('price',0):.2f} ({i.get('change_pct',0):+.2f}%)"
            for i in indices[:3]
        )
    except Exception:
        idx_text = "数据暂不可用"
    subject = f"AlphaEye 盘前 · {today.strftime('%m/%d')} {wday}"
    body = f"""<h2>AlphaEye 盘前计划</h2>
<p><strong>{today.strftime('%Y年%m月%d日')} {wday}</strong></p>
<h3>昨日收盘</h3><p>{idx_text}</p>
<h3>今日纪律</h3>
<ol><li>开盘30分钟不追第一波急拉</li>
<li>板块不联动的单票不要碰</li>
<li>风险分高的票只记录不验证</li></ol>
<p>打开 <a href="http://47.102.106.104:8501">AlphaEye</a> 查看完整雷达。</p>
<p style="color:#888;font-size:12px">AlphaEye Research OS · 自动生成</p>"""
    return send_email(subject, body)


def closing_push() -> bool:
    """收盘总结推送（15:07 触发）"""
    today = date.today()
    try:
        from src.data.realtime import get_market_overview, get_top_stocks
        ov = get_market_overview()
        indices = ov.get("indices", [])
        idx_text = " | ".join(
            f"{i.get('name','')} {i.get('price',0):.2f} ({i.get('change_pct',0):+.2f}%)"
            for i in indices[:3]
        )
        up = get_top_stocks("changepercent", False, 5) or []
        up_text = "<br>".join(f"{s.get('name','')} {s.get('change_pct',0):+.2f}%" for s in up[:5])
    except Exception:
        idx_text = "数据暂不可用"
        up_text = "数据暂不可用"
    subject = f"AlphaEye 收盘 · {today.strftime('%m/%d')}"
    body = f"""<h2>AlphaEye 收盘总结</h2>
<p><strong>{today.strftime('%Y年%m月%d日')}</strong></p>
<h3>今日大盘</h3><p>{idx_text}</p>
<h3>今日领涨</h3><p>{up_text}</p>
<p>打开 <a href="http://47.102.106.104:8501">AlphaEye</a> 查看 AI 收盘复盘。</p>
<p style="color:#888;font-size:12px">AlphaEye Research OS · 自动生成</p>"""
    return send_email(subject, body)


def radar_alert(alert_title: str, alert_body: str) -> bool:
    """雷达异动推送"""
    subject = f"AlphaEye 雷达异动 · {alert_title}"
    body = f"""<h2>AlphaEye 雷达异动</h2>
<p><strong>{alert_title}</strong></p><p>{alert_body}</p>
<p>打开 <a href="http://47.102.106.104:8501">AlphaEye</a> 查看详情。</p>
<p style="color:#888;font-size:12px">AlphaEye Research OS · 自动生成</p>"""
    return send_email(subject, body)
