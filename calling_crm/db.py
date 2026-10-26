from __future__ import annotations

import json
import hashlib
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

STATUSES = ("new", "contacted", "lead", "followup", "booked", "closed", "no_answer", "busy", "information", "interested", "call_back", "not_interested", "do_not_contact")

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, company TEXT DEFAULT '', followup_days INTEGER NOT NULL DEFAULT 5, sender_name TEXT DEFAULT '', sender_email TEXT DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL DEFAULT 1, name TEXT NOT NULL, phone TEXT, email TEXT, company TEXT, address TEXT DEFAULT '', product TEXT, status TEXT NOT NULL DEFAULT 'new', notes TEXT DEFAULT '', consent_marketing INTEGER NOT NULL DEFAULT 0, consent_information INTEGER NOT NULL DEFAULT 0, consent_followup INTEGER NOT NULL DEFAULT 0, consent_source TEXT DEFAULT '', consent_at TEXT, consent_purpose TEXT DEFAULT '', legal_basis TEXT DEFAULT '', opted_out_at TEXT, retention_until TEXT, archived_at TEXT, archive_reason TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL, name TEXT NOT NULL, description TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL, product_id INTEGER, package_name TEXT NOT NULL, description TEXT DEFAULT '', price TEXT DEFAULT 'Pris lämnas efter överenskommelse', vat TEXT DEFAULT '', min_participants TEXT DEFAULT '', max_participants TEXT DEFAULT '', duration TEXT DEFAULT '', terms TEXT DEFAULT '', valid_until TEXT DEFAULT '', version INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS templates (id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL, name TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL, provider TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT, notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS followups (id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL, due_date TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'call', status TEXT NOT NULL DEFAULT 'open', notes TEXT DEFAULT '', created_at TEXT NOT NULL, completed_at TEXT);
CREATE TABLE IF NOT EXISTS consent_events (id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL, purpose TEXT NOT NULL, channel TEXT NOT NULL, granted INTEGER NOT NULL, source TEXT NOT NULL, recorded_by TEXT DEFAULT '', recorded_at TEXT NOT NULL, revoked_at TEXT);
CREATE TABLE IF NOT EXISTS sent_offers (id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL, offer_id INTEGER, template_id INTEGER, recipient TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, sent_at TEXT NOT NULL, delivery_status TEXT NOT NULL DEFAULT 'draft');
CREATE TABLE IF NOT EXISTS contact_events (id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL, event_type TEXT NOT NULL, status TEXT, body TEXT DEFAULT '', created_at TEXT NOT NULL, metadata TEXT DEFAULT '{}', FOREIGN KEY(contact_id) REFERENCES contacts(id));
CREATE TABLE IF NOT EXISTS quotes (id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL, offer_id INTEGER, version INTEGER NOT NULL DEFAULT 1, title TEXT NOT NULL, data_json TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(contact_id) REFERENCES contacts(id));
CREATE TABLE IF NOT EXISTS import_batches (id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL, filename TEXT NOT NULL, created_at TEXT NOT NULL, imported_ids TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL DEFAULT 1, name TEXT NOT NULL, product TEXT DEFAULT '', purpose TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_registry (id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL, source_type TEXT NOT NULL, original_filename TEXT NOT NULL, original_path TEXT DEFAULT '', relative_path TEXT DEFAULT '', imported_at TEXT NOT NULL, sha256 TEXT NOT NULL, import_batch_id INTEGER, source_version TEXT DEFAULT '', UNIQUE(profile_id,sha256,original_filename));
CREATE TABLE IF NOT EXISTS contact_sources (contact_id INTEGER NOT NULL, source_id INTEGER NOT NULL, PRIMARY KEY(contact_id,source_id), FOREIGN KEY(contact_id) REFERENCES contacts(id), FOREIGN KEY(source_id) REFERENCES source_registry(id));
CREATE TABLE IF NOT EXISTS product_sources (product_id INTEGER NOT NULL, source_id INTEGER NOT NULL, PRIMARY KEY(product_id,source_id), FOREIGN KEY(product_id) REFERENCES products(id), FOREIGN KEY(source_id) REFERENCES source_registry(id));
CREATE TABLE IF NOT EXISTS offer_sources (offer_id INTEGER NOT NULL, source_id INTEGER NOT NULL, PRIMARY KEY(offer_id,source_id), FOREIGN KEY(offer_id) REFERENCES offers(id), FOREIGN KEY(source_id) REFERENCES source_registry(id));
CREATE TABLE IF NOT EXISTS source_import_batches (source_id INTEGER NOT NULL, import_batch_id INTEGER NOT NULL, PRIMARY KEY(source_id,import_batch_id), FOREIGN KEY(source_id) REFERENCES source_registry(id), FOREIGN KEY(import_batch_id) REFERENCES import_batches(id));
"""

def now() -> str: return datetime.now().isoformat(timespec="seconds")

class Database:
    def __init__(self, path: str | Path):
        database_path=Path(path).expanduser(); database_path.parent.mkdir(parents=True,exist_ok=True)
        self.path = str(database_path); self.conn = sqlite3.connect(self.path, check_same_thread=False); self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON"); self.conn.execute("PRAGMA busy_timeout=5000"); self.conn.executescript(SCHEMA); self._migrate(); self.conn.commit()
    def _migrate(self):
        cols={r[1] for r in self.conn.execute("PRAGMA table_info(contacts)")}
        for n,d in (("profile_id","INTEGER NOT NULL DEFAULT 1"),("address","TEXT DEFAULT ''"),("postal_code","TEXT DEFAULT ''"),("city","TEXT DEFAULT ''"),("country","TEXT DEFAULT ''"),("status","TEXT NOT NULL DEFAULT 'new'"),("consent_information","INTEGER NOT NULL DEFAULT 0"),("consent_followup","INTEGER NOT NULL DEFAULT 0"),("archived_at","TEXT"),("archive_reason","TEXT DEFAULT ''")):
            if n not in cols: self.conn.execute(f"ALTER TABLE contacts ADD COLUMN {n} {d}")
        self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS contacts_profile_phone ON contacts(profile_id,phone) WHERE phone IS NOT NULL AND phone <> ''")
        self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS contacts_profile_email ON contacts(profile_id,email) WHERE email IS NOT NULL AND email <> ''")
        batch_cols={r[1] for r in self.conn.execute("PRAGMA table_info(import_batches)")}
        if "source_id" not in batch_cols: self.conn.execute("ALTER TABLE import_batches ADD COLUMN source_id INTEGER")
        template_cols={r[1] for r in self.conn.execute("PRAGMA table_info(templates)")}
        for n,d in (("profile_id","INTEGER NOT NULL DEFAULT 1"),("version","INTEGER NOT NULL DEFAULT 1"),("active","INTEGER NOT NULL DEFAULT 1")):
            if n not in template_cols: self.conn.execute(f"ALTER TABLE templates ADD COLUMN {n} {d}")
        campaign_cols={r[1] for r in self.conn.execute("PRAGMA table_info(campaigns)")}
        if "profile_id" not in campaign_cols: self.conn.execute("ALTER TABLE campaigns ADD COLUMN profile_id INTEGER NOT NULL DEFAULT 1")
        if not self.conn.execute("SELECT 1 FROM profiles LIMIT 1").fetchone(): self.conn.execute("INSERT INTO profiles(name,created_at) VALUES(?,?)",("Standardprofil",now()))
        for profile in self.conn.execute("SELECT id FROM profiles"):
            if not self.conn.execute("SELECT 1 FROM templates WHERE profile_id=? LIMIT 1",(profile[0],)).fetchone():
                self.conn.execute("INSERT INTO templates(profile_id,name,subject,body) VALUES(?,?,?,?)",(profile[0],"Informationsförfrågan","Information om {{erbjudandepaket}} för {{företagsnamn}}","Hej {{kontaktperson}},\n\nTack för vårt samtal. Här kommer den efterfrågade informationen om {{produkt}} / {{erbjudandepaket}}.\n\nPris: {{pris}}\nDeltagarantal: {{deltagarantal}}\nVillkor: {{villkor}}\n\nVänliga hälsningar,\n{{avsändare}}"))
    def close(self): self.conn.close()
    def _rows(self, sql, args=()): return self.conn.execute(sql,args).fetchall()
    def profiles(self): return self._rows("SELECT * FROM profiles ORDER BY name")
    def profile(self, pid): return self.conn.execute("SELECT * FROM profiles WHERE id=?",(pid,)).fetchone()
    def create_profile(self,name,company="",followup_days=5,sender_name="",sender_email=""):
        cur=self.conn.execute("INSERT INTO profiles(name,company,followup_days,sender_name,sender_email,created_at) VALUES(?,?,?,?,?,?)",(name,company,followup_days,sender_name,sender_email,now())); self.conn.commit(); return cur.lastrowid
    def update_profile(self,pid,**fields):
        allowed={"name","company","followup_days","sender_name","sender_email"}; fields={k:v for k,v in fields.items() if k in allowed}
        if "followup_days" in fields and int(fields["followup_days"])<0: raise ValueError("Uppföljningsdagar kan inte vara negativa")
        if fields: self.conn.execute(f"UPDATE profiles SET {','.join(f'{k}=?' for k in fields)} WHERE id=?",(*fields.values(),pid)); self.conn.commit()
    def list_contacts(self, profile_id=1, search="", limit=500, include_archived=False):
        like=f"%{search}%"; archived="" if include_archived else " AND archived_at IS NULL"; return self._rows(f"SELECT * FROM contacts WHERE profile_id=?{archived} AND (name LIKE ? OR company LIKE ? OR phone LIKE ? OR email LIKE ?) ORDER BY updated_at DESC LIMIT ?",(profile_id,like,like,like,like,limit))
    def get_contact(self,cid): return self.conn.execute("SELECT * FROM contacts WHERE id=?",(cid,)).fetchone()
    def source(self,source_id): return self.conn.execute("SELECT * FROM source_registry WHERE id=?",(source_id,)).fetchone()
    def sources_for_contact(self,cid): return self._rows("SELECT s.* FROM source_registry s JOIN contact_sources cs ON cs.source_id=s.id WHERE cs.contact_id=? ORDER BY s.imported_at DESC",(cid,))
    def sources_for_product(self,pid): return self._rows("SELECT s.* FROM source_registry s JOIN product_sources ps ON ps.source_id=s.id WHERE ps.product_id=? ORDER BY s.imported_at DESC",(pid,))
    def sources_for_offer(self,oid): return self._rows("SELECT s.* FROM source_registry s JOIN offer_sources os ON os.source_id=s.id WHERE os.offer_id=? ORDER BY s.imported_at DESC",(oid,))
    def register_source(self, profile_id, source_type, original_filename, original_path="", import_batch_id=None, source_version="", managed_copy=None):
        if source_type not in {"excel","csv","document","manual"}: raise ValueError("Okänd källtyp")
        path=Path(original_path).expanduser() if original_path else None
        digest=""
        if path and path.is_file(): digest=hashlib.sha256(path.read_bytes()).hexdigest()
        elif managed_copy and Path(managed_copy).is_file(): digest=hashlib.sha256(Path(managed_copy).read_bytes()).hexdigest()
        else: digest=hashlib.sha256((source_type+"|"+original_filename+"|"+source_version).encode()).hexdigest()
        relative=""
        candidate=Path(managed_copy or original_path).expanduser() if (managed_copy or original_path) else None
        if candidate and candidate.is_absolute():
            try: relative=str(candidate.relative_to(Path(self.path).resolve().parent))
            except ValueError: relative=""
        existing=self.conn.execute("SELECT id FROM source_registry WHERE profile_id=? AND sha256=? AND original_filename=?",(profile_id,digest,original_filename)).fetchone()
        if existing:
            if import_batch_id: self.conn.execute("UPDATE source_registry SET import_batch_id=? WHERE id=?",(import_batch_id,existing[0])); self.conn.commit()
            return existing[0]
        cur=self.conn.execute("INSERT INTO source_registry(profile_id,source_type,original_filename,original_path,relative_path,imported_at,sha256,import_batch_id,source_version) VALUES(?,?,?,?,?,?,?,?,?)",(profile_id,source_type,original_filename, str(path or ""),relative,now(),digest,import_batch_id,source_version)); self.conn.commit(); return cur.lastrowid
    def link_contact_source(self,cid,sid): self.conn.execute("INSERT OR IGNORE INTO contact_sources(contact_id,source_id) VALUES(?,?)",(cid,sid)); self.conn.commit()
    def link_product_source(self,pid,sid): self.conn.execute("INSERT OR IGNORE INTO product_sources(product_id,source_id) VALUES(?,?)",(pid,sid)); self.conn.commit()
    def link_offer_source(self,oid,sid): self.conn.execute("INSERT OR IGNORE INTO offer_sources(offer_id,source_id) VALUES(?,?)",(oid,sid)); self.conn.commit()
    def resolve_source_path(self,sid):
        source=self.source(sid)
        if not source: return None
        candidates=[]
        if source["original_path"]: candidates.append(Path(source["original_path"]))
        if source["relative_path"]: candidates.append(Path(self.path).resolve().parent/source["relative_path"])
        for candidate in candidates:
            if candidate.is_file(): return candidate
        return None
    def source_available(self,sid): return self.resolve_source_path(sid) is not None
    def repoint_source(self,sid,new_path):
        source=self.source(sid); path=Path(new_path).expanduser().resolve()
        if not source: raise ValueError("Källan finns inte")
        if not path.is_file(): raise FileNotFoundError(path)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != source["sha256"]: raise ValueError("Filen har annan SHA-256-hash än registrerad källa")
        relative=""
        try: relative=str(path.relative_to(Path(self.path).resolve().parent))
        except ValueError: pass
        self.conn.execute("UPDATE source_registry SET original_path=?,relative_path=? WHERE id=?",(str(path),relative,sid)); self.conn.commit()
        return path
    def upsert_contact(self,data:dict[str,Any],profile_id=1):
        phone=str(data.get("phone") or "").strip(); email=str(data.get("email") or "").strip().lower(); stamp=now(); existing=None
        if phone: existing=self.conn.execute("SELECT id FROM contacts WHERE profile_id=? AND phone=?",(profile_id,phone)).fetchone()
        if not existing and email: existing=self.conn.execute("SELECT id FROM contacts WHERE profile_id=? AND email=?",(profile_id,email)).fetchone()
        fields={"profile_id":profile_id,"name":data.get("name") or "","phone":phone,"email":email,"company":data.get("company", ""),"address":data.get("address", ""),"postal_code":data.get("postal_code", ""),"city":data.get("city", ""),"country":data.get("country", ""),"product":data.get("product", ""),"notes":data.get("notes", "")}
        if existing:
            fields={k:v for k,v in fields.items() if k != "profile_id" and v not in (None,"")}
            if data.get("consent_marketing") and data.get("consent_source") != "import": fields.update(consent_marketing=1,consent_source=data.get("consent_source","manual"),consent_at=stamp,consent_purpose=data.get("consent_purpose","information"),legal_basis=data.get("legal_basis","samtycke"))
            if fields:
                sets=",".join(f"{k}=?" for k in fields); self.conn.execute(f"UPDATE contacts SET {sets},updated_at=? WHERE id=?",(*fields.values(),stamp,existing[0])); self.conn.commit()
            return existing[0],False
        fields["name"]=fields["name"] or fields["company"] or "Okänd"
        fields.update(consent_marketing=0,consent_information=0,consent_followup=0,consent_source="",consent_at=None,consent_purpose="",legal_basis="")
        cur=self.conn.execute("INSERT INTO contacts(profile_id,name,phone,email,company,address,postal_code,city,country,product,notes,consent_marketing,consent_information,consent_followup,consent_source,consent_at,consent_purpose,legal_basis,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(*fields.values(),stamp,stamp)); self.conn.commit(); return cur.lastrowid,True
    def update_contact(self,cid,**fields):
        allowed={"name","phone","email","company","address","postal_code","city","country","product","status","notes","retention_until"}; fields={k:v for k,v in fields.items() if k in allowed}
        if fields: self.conn.execute(f"UPDATE contacts SET {','.join(f'{k}=?' for k in fields)},updated_at=? WHERE id=?",(*fields.values(),now(),cid)); self.conn.commit()
    def set_consent(self,cid,granted,purpose="information",channel="email",source="manual",recorded_by="user"):
        stamp=now(); self.conn.execute("INSERT INTO consent_events(contact_id,purpose,channel,granted,source,recorded_by,recorded_at) VALUES(?,?,?,?,?,?,?)",(cid,purpose,channel,int(granted),source,recorded_by,stamp))
        column={"information":"consent_information","marketing":"consent_marketing","followup":"consent_followup"}.get(purpose,"consent_information")
        self.conn.execute(f"UPDATE contacts SET {column}=?,consent_source=?,consent_at=?,consent_purpose=?,legal_basis=?,opted_out_at=? WHERE id=?",(int(granted),source,stamp,purpose,"samtycke" if granted else "",None if granted else stamp,cid)); self.conn.commit()
    def set_opt_out(self,cid):
        self.set_consent(cid,False,purpose="marketing",source="manual-opt-out"); self.set_consent(cid,False,purpose="information",source="manual-opt-out"); self.set_consent(cid,False,purpose="followup",source="manual-opt-out")
    def eligible_for_marketing(self,cid):
        r=self.get_contact(cid); return bool(r and r["email"] and r["consent_marketing"] and not r["opted_out_at"])
    def eligible_for_information(self,cid):
        r=self.get_contact(cid); return bool(r and r["email"] and r["consent_information"] and not r["opted_out_at"])
    def eligible_for_followup(self,cid):
        r=self.get_contact(cid); return bool(r and r["consent_followup"] and not r["opted_out_at"])
    def add_event(self,cid,event_type,body="",status=None,metadata=None):
        self.conn.execute("INSERT INTO contact_events(contact_id,event_type,status,body,created_at,metadata) VALUES(?,?,?,?,?,?)",(cid,event_type,status,body,now(),json.dumps(metadata or {},ensure_ascii=False))); self.conn.commit()
    def events_for(self,cid): return self._rows("SELECT * FROM contact_events WHERE contact_id=? ORDER BY created_at DESC,id DESC",(cid,))
    def log_call(self,cid,provider,status,notes="",ended_at=None):
        self.conn.execute("INSERT INTO calls(contact_id,provider,status,started_at,ended_at,notes) VALUES(?,?,?,?,?,?)",(cid,provider,status,now(),ended_at,notes)); self.update_contact(cid,status=status,notes=notes or (self.get_contact(cid)["notes"] if self.get_contact(cid) else "")); self.add_event(cid,"call",notes,status=status,metadata={"provider":provider}); self.conn.commit()
    def calls_for(self,cid): return self._rows("SELECT * FROM calls WHERE contact_id=? ORDER BY started_at DESC",(cid,))
    def create_followup(self,cid,due_date=None,notes=""):
        r=self.get_contact(cid); p=self.profile(r["profile_id"]); due=due_date or (date.today()+timedelta(days=int(p["followup_days"]))).isoformat(); cur=self.conn.execute("INSERT INTO followups(contact_id,due_date,notes,created_at) VALUES(?,?,?,?)",(cid,due,notes,now())); self.update_contact(cid,status="followup"); self.add_event(cid,"followup",notes,status="followup",metadata={"due_date":due}); self.conn.commit(); return cur.lastrowid
    def followups(self,pid=1,bucket="all"):
        clause="" if bucket=="all" else " AND f.status='open' AND f.due_date<=date('now')" if bucket in ("today","overdue") else " AND f.status='open' AND f.due_date>date('now')"
        if bucket=="overdue": clause += " AND f.due_date<date('now')"
        return self._rows(f"SELECT f.*,c.name,c.company,c.phone FROM followups f JOIN contacts c ON c.id=f.contact_id WHERE c.profile_id=?{clause} ORDER BY f.due_date",(pid,))
    def complete_followup(self,fid):
        row=self.conn.execute("SELECT contact_id FROM followups WHERE id=?",(fid,)).fetchone(); self.conn.execute("UPDATE followups SET status='completed',completed_at=? WHERE id=?",(now(),fid));
        if row: self.add_event(row[0],"followup_completed",status="contacted")
        self.conn.commit()
    def archive_contact(self,cid,reason="user"):
        stamp=now(); self.conn.execute("UPDATE contacts SET archived_at=?,archive_reason=?,updated_at=? WHERE id=?",(stamp,reason,stamp,cid)); self.add_event(cid,"archived",reason); self.conn.commit()
    def restore_contact(self,cid):
        self.conn.execute("UPDATE contacts SET archived_at=NULL,archive_reason='',updated_at=? WHERE id=?",(now(),cid)); self.add_event(cid,"restored"); self.conn.commit()
    def save_notes(self,cid,notes):
        self.update_contact(cid,notes=notes); self.add_event(cid,"note",notes)
    def create_quote(self,cid,title,data,offer_id=None):
        previous=self.conn.execute("SELECT COALESCE(MAX(version),0) FROM quotes WHERE contact_id=?",(cid,)).fetchone()[0]; cur=self.conn.execute("INSERT INTO quotes(contact_id,offer_id,version,title,data_json,created_at) VALUES(?,?,?,?,?,?)",(cid,offer_id,previous+1,title,json.dumps(data,ensure_ascii=False),now())); self.add_event(cid,"quote_created",title,metadata={"quote_id":cur.lastrowid,"version":previous+1}); self.conn.commit(); return cur.lastrowid,previous+1
    def quotes_for(self,cid): return self._rows("SELECT * FROM quotes WHERE contact_id=? ORDER BY version DESC",(cid,))
    def products(self,pid=1): return self._rows("SELECT * FROM products WHERE profile_id=? AND active=1 ORDER BY name",(pid,))
    def product(self,pid): return self.conn.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
    def create_product(self,pid,name,description="",source_id=None):
        if not name.strip(): raise ValueError("Produktnamn krävs")
        cur=self.conn.execute("INSERT INTO products(profile_id,name,description) VALUES(?,?,?)",(pid,name.strip(),description));
        if source_id: self.conn.execute("INSERT OR IGNORE INTO product_sources(product_id,source_id) VALUES(?,?)",(cur.lastrowid,source_id))
        self.conn.commit(); return cur.lastrowid
    def update_product(self,product_id,**fields):
        allowed={"name","description","active"}; fields={k:v for k,v in fields.items() if k in allowed}
        if "name" in fields and not fields["name"].strip(): raise ValueError("Produktnamn krävs")
        if fields: self.conn.execute(f"UPDATE products SET {','.join(f'{k}=?' for k in fields)} WHERE id=?",(*fields.values(),product_id)); self.conn.commit()
    def offers(self,pid=1): return self._rows("SELECT * FROM offers WHERE profile_id=? AND active=1 ORDER BY package_name",(pid,))
    def offer(self,oid): return self.conn.execute("SELECT * FROM offers WHERE id=?",(oid,)).fetchone()
    def create_offer(self,pid,product_id,package_name,description,price,vat,min_participants,max_participants,duration,terms,valid_until="",source_id=None):
        if not package_name.strip(): raise ValueError("Paketnamn krävs")
        if not str(price).strip(): raise ValueError("Pris krävs; använd exempelvis 'Pris lämnas efter överenskommelse' om pris saknas")
        if min_participants and max_participants and int(min_participants)>int(max_participants): raise ValueError("Minsta deltagarantal kan inte vara större än högsta")
        cur=self.conn.execute("INSERT INTO offers(profile_id,product_id,package_name,description,price,vat,min_participants,max_participants,duration,terms,valid_until,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(pid,product_id,package_name,description,price,vat,min_participants,max_participants,duration,terms,valid_until,now()));
        if source_id: self.conn.execute("INSERT OR IGNORE INTO offer_sources(offer_id,source_id) VALUES(?,?)",(cur.lastrowid,source_id))
        self.conn.commit(); return cur.lastrowid
    def update_offer(self,offer_id,**fields):
        allowed={"product_id","package_name","description","price","vat","min_participants","max_participants","duration","terms","valid_until","active"}; fields={k:v for k,v in fields.items() if k in allowed}
        if "price" in fields and not str(fields["price"]).strip(): raise ValueError("Pris krävs")
        if fields: self.conn.execute(f"UPDATE offers SET {','.join(f'{k}=?' for k in fields)},version=version+1 WHERE id=?",(*fields.values(),offer_id)); self.conn.commit()
    def templates(self,pid=1): return self._rows("SELECT * FROM templates WHERE profile_id=? AND active=1 ORDER BY name",(pid,))
    def template(self,tid): return self.conn.execute("SELECT * FROM templates WHERE id=?",(tid,)).fetchone()
    def add_template(self,pid,name,subject,body):
        if not name.strip() or not subject.strip() or not body.strip(): raise ValueError("Mallnamn, ämne och innehåll krävs")
        cur=self.conn.execute("INSERT INTO templates(profile_id,name,subject,body) VALUES(?,?,?,?)",(pid,name,subject,body)); self.conn.commit(); return cur.lastrowid
    def update_template(self,template_id,**fields):
        allowed={"name","subject","body","active"}; fields={k:v for k,v in fields.items() if k in allowed}
        if fields: self.conn.execute(f"UPDATE templates SET {','.join(f'{k}=?' for k in fields)},version=version+1 WHERE id=?",(*fields.values(),template_id)); self.conn.commit()
    def record_sent_offer(self,cid,oid,tid,recipient,subject,body,status="sent"):
        cur=self.conn.execute("INSERT INTO sent_offers(contact_id,offer_id,template_id,recipient,subject,body,sent_at,delivery_status) VALUES(?,?,?,?,?,?,?,?)",(cid,oid,tid,recipient,subject,body,now(),status)); self.add_event(cid,"email",subject,status=status); self.conn.commit(); return cur.lastrowid
    def sent_offers_for(self,cid): return self._rows("SELECT * FROM sent_offers WHERE contact_id=? ORDER BY sent_at DESC",(cid,))
    def update_email_status(self,email_id,status):
        row=self.conn.execute("SELECT contact_id FROM sent_offers WHERE id=?",(email_id,)).fetchone()
        self.conn.execute("UPDATE sent_offers SET delivery_status=? WHERE id=?",(status,email_id))
        if row: self.add_event(row[0],"email_status",status=status)
        self.conn.commit()
    def add_followup_after_offer(self,cid):
        if not self.eligible_for_followup(cid): raise PermissionError("Uppföljning kräver dokumenterat uppföljningsmedgivande och får inte vara spärrad")
        return self.create_followup(cid)
    def import_batch(self,pid,filename,ids,source_id=None):
        cur=self.conn.execute("INSERT INTO import_batches(profile_id,filename,created_at,imported_ids,source_id) VALUES(?,?,?,?,?)",(pid,filename,now(),json.dumps(ids),source_id)); batch_id=cur.lastrowid
        if source_id:
            self.conn.execute("UPDATE source_registry SET import_batch_id=? WHERE id=?",(batch_id,source_id)); self.conn.execute("INSERT OR IGNORE INTO source_import_batches(source_id,import_batch_id) VALUES(?,?)",(source_id,batch_id))
        self.conn.commit(); return batch_id
    def undo_last_import(self,pid):
        batch=self.conn.execute("SELECT * FROM import_batches WHERE profile_id=? ORDER BY id DESC LIMIT 1",(pid,)).fetchone()
        if not batch:return 0
        ids=json.loads(batch["imported_ids"]); n=0
        for cid in ids:
            if not self.conn.execute("SELECT 1 FROM calls WHERE contact_id=? UNION SELECT 1 FROM followups WHERE contact_id=?",(cid,cid)).fetchone(): self.conn.execute("DELETE FROM contacts WHERE id=?",(cid,)); n+=1
        self.conn.execute("DELETE FROM import_batches WHERE id=?",(batch["id"],)); self.conn.commit(); return n
    def queue_counts(self,pid=1):
        base={"contacts":self.conn.execute("SELECT count(*) FROM contacts WHERE profile_id=? AND archived_at IS NULL",(pid,)).fetchone()[0],"new":self.conn.execute("SELECT count(*) FROM contacts WHERE profile_id=? AND status='new' AND archived_at IS NULL",(pid,)).fetchone()[0],"offers":self.conn.execute("SELECT count(*) FROM contacts WHERE profile_id=? AND consent_marketing=1 AND email<>'' AND opted_out_at IS NULL AND archived_at IS NULL",(pid,)).fetchone()[0]}
        base["today"]=self.conn.execute("SELECT count(*) FROM followups f JOIN contacts c ON c.id=f.contact_id WHERE c.profile_id=? AND c.archived_at IS NULL AND f.status='open' AND f.due_date=date('now')",(pid,)).fetchone()[0]
        base["overdue"]=self.conn.execute("SELECT count(*) FROM followups f JOIN contacts c ON c.id=f.contact_id WHERE c.profile_id=? AND c.archived_at IS NULL AND f.status='open' AND f.due_date<date('now')",(pid,)).fetchone()[0]
        base["followups"]=base["today"]+base["overdue"]; return base
