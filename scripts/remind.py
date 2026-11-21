#!/usr/bin/env python3
"""日迹 · 定时邮件提醒
由 GitHub Actions 每 30 分钟跑一次，到点发邮件。
配置在仓库根目录的 reminders.json，密码走环境变量（仓库 Secrets）。
"""
import json, os, smtplib, ssl, sys
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

TZ = timezone(timedelta(hours=8))
now = datetime.now(TZ)
today = now.date()


def load(path="reminders.json"):
    for p in (path, os.path.join(os.path.dirname(__file__), "..", path)):
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    print("reminders.json not found")
    sys.exit(0)


def due_lines(cfg):
    out = []

    daily = cfg.get("daily") or {}
    t = daily.get("time")
    if t:
        try:
            hh, mm = [int(x) for x in str(t).split(":")[:2]]
            slot = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if slot <= now < slot + timedelta(minutes=30):
                out.append(daily.get("text") or "记一下今天。")
        except Exception:
            pass

    for d in cfg.get("days") or []:
        try:
            dt = datetime.strptime(d["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        delta = (dt - today).days
        title = d.get("title") or "纪念日"
        lead = int(d.get("lead") or 0)
        if delta == 0:
            out.append("%s就是今天。" % title)
        elif lead and delta == lead:
            out.append("%s还有 %d 天（%d月%d日）。" % (title, lead, dt.month, dt.day))
    return out


def main():
    cfg = load()
    lines = due_lines(cfg)
    if not lines:
        print("nothing due at", now.strftime("%Y-%m-%d %H:%M"))
        return

    smtp = cfg.get("smtp") or {}
    host = smtp.get("host", "smtp.qq.com")
    port = int(smtp.get("port", 465))
    user = os.environ.get("MAIL_USER", "")
    pwd = os.environ.get("MAIL_PASS", "")
    to = os.environ.get("MAIL_TO", "") or user

    body = "\n".join(lines)
    print("due:", body)

    if not (user and pwd and to):
        print("missing MAIL_USER / MAIL_PASS / MAIL_TO -> dry run, not sending")
        return

    msg = EmailMessage()
    msg["Subject"] = "日迹 · " + lines[0][:24]
    msg["From"] = user
    msg["To"] = to
    msg.set_content(body + "\n\n—— 日迹 \nhttps://liaun.github.io/riji/")

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=ctx, timeout=25) as s:
        s.login(user, pwd)
        s.send_message(msg)
    print("sent to", to)


if __name__ == "__main__":
    main()
