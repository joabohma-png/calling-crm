from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

class MailError(RuntimeError): pass

def render_template(template, contact, offer, product, profile):
    values={
        "kontaktperson":contact["name"], "företagsnamn":contact["company"] or contact["name"],
        "produkt":product["name"] if product else "", "erbjudandepaket":offer["package_name"],
        "pris":offer["price"], "deltagarantal":f"{offer['min_participants'] or '–'}–{offer['max_participants'] or '–'}",
        "villkor":offer["terms"], "avsändare":profile["sender_name"] or profile["company"],
    }
    subject=template["subject"]; body=template["body"]
    for key,value in values.items():
        subject=subject.replace("{{"+key+"}}",str(value or "")); body=body.replace("{{"+key+"}}",str(value or ""))
    return subject,body

def make_message(sender, recipient, subject, body, attachment_path=None):
    if not sender or not recipient: raise MailError("Avsändare och mottagare krävs")
    msg=EmailMessage(); msg["From"]=sender; msg["To"]=recipient; msg["Subject"]=subject; msg.set_content(body)
    if attachment_path:
        from pathlib import Path
        path=Path(attachment_path)
        if not path.is_file(): raise MailError("PDF-bilagan saknas")
        msg.add_attachment(path.read_bytes(), maintype="application", subtype="pdf", filename=path.name)
    return msg

def send_smtp(message, host, port, username, password, use_tls=True, timeout=20):
    if not password: raise MailError("SMTP-lösenord saknas; lösenord lagras inte av CRM")
    try:
        if use_tls:
            with smtplib.SMTP(host,port,timeout=timeout) as server:
                server.ehlo(); server.starttls(context=ssl.create_default_context()); server.ehlo(); server.login(username,password); server.send_message(message)
        else:
            with smtplib.SMTP_SSL(host,port,timeout=timeout,context=ssl.create_default_context()) as server:
                server.login(username,password); server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise MailError(f"SMTP-utskick misslyckades: {exc}") from exc
