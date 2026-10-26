import hashlib
import tempfile
import unittest
from pathlib import Path

from calling_crm.db import Database

class SourceReferenceTests(unittest.TestCase):
    def test_source_metadata_is_deduplicated_and_links_customer_and_batch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); db=Database(root/'crm.db'); pid=db.profiles()[0]['id']; source_file=root/'customers.csv'; source_file.write_text('Namn;Telefon\nTest;0700\n',encoding='utf-8')
            sid=db.register_source(pid,'csv',source_file.name,str(source_file),source_version='2026-01'); cid,_=db.upsert_contact({'name':'Test','phone':'0700'},pid); db.link_contact_source(cid,sid); batch=db.import_batch(pid,source_file.name,[cid],sid)
            self.assertEqual(db.register_source(pid,'csv',source_file.name,str(source_file),source_version='2026-01'),sid)
            source=db.source(sid); self.assertEqual(source['sha256'],hashlib.sha256(source_file.read_bytes()).hexdigest()); self.assertEqual(source['import_batch_id'],batch); self.assertEqual(db.sources_for_contact(cid)[0]['id'],sid)
            db.close()

    def test_missing_source_keeps_customer_and_repoint_requires_matching_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); db=Database(root/'crm.db'); pid=db.profiles()[0]['id']; original=root/'old.csv'; original.write_text('original',encoding='utf-8'); sid=db.register_source(pid,'csv','old.csv',str(original)); cid,_=db.upsert_contact({'name':'Kund','email':'kund@example.test'},pid); db.link_contact_source(cid,sid); original.unlink()
            self.assertIsNone(db.resolve_source_path(sid)); self.assertEqual(db.get_contact(cid)['name'],'Kund')
            moved=root/'moved.csv'; moved.write_text('wrong',encoding='utf-8')
            with self.assertRaises(ValueError): db.repoint_source(sid,moved)
            moved.write_text('original',encoding='utf-8'); db.repoint_source(sid,moved); self.assertEqual(db.resolve_source_path(sid),moved.resolve()); db.close()

    def test_portable_relative_managed_copy_survives_missing_original(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); db=Database(root/'data'/'crm.db'); pid=db.profiles()[0]['id']; managed=root/'data'/'sources'/'hash-file.csv'; managed.parent.mkdir(parents=True); managed.write_text('portable',encoding='utf-8'); sid=db.register_source(pid,'csv','file.csv','/removed/original/file.csv',managed_copy=managed)
            source=db.source(sid); self.assertTrue(source['relative_path']); self.assertEqual(db.resolve_source_path(sid),managed.resolve()); db.close()

    def test_external_product_and_offer_sources_are_supported(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); db=Database(root/'crm.db'); pid=db.profiles()[0]['id']; sid=db.register_source(pid,'document','price-list.pdf',source_version='v2'); product=db.create_product(pid,'Tjänst',source_id=sid); offer=db.create_offer(pid,product,'Paket','','100 kr','','1','5','','Villkor',source_id=sid)
            self.assertEqual(db.sources_for_product(product)[0]['id'],sid); self.assertEqual(db.sources_for_offer(offer)[0]['id'],sid); db.close()

    def test_legacy_database_migrates_without_losing_customer_or_template(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'legacy.db'
            import sqlite3
            conn=sqlite3.connect(path)
            conn.executescript("""CREATE TABLE contacts (id INTEGER PRIMARY KEY,name TEXT NOT NULL,phone TEXT,email TEXT,company TEXT,product TEXT,notes TEXT DEFAULT '',consent_marketing INTEGER NOT NULL DEFAULT 0,consent_source TEXT DEFAULT '',consent_at TEXT,consent_purpose TEXT DEFAULT '',legal_basis TEXT DEFAULT '',opted_out_at TEXT,retention_until TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL); CREATE TABLE templates (id INTEGER PRIMARY KEY,campaign_id INTEGER,name TEXT NOT NULL,subject TEXT NOT NULL,body TEXT NOT NULL);""")
            conn.execute("INSERT INTO contacts(name,email,created_at,updated_at) VALUES(?,?,?,?)",('Legacy','legacy@example.test','2026-01-01','2026-01-01')); conn.execute("INSERT INTO templates(name,subject,body) VALUES(?,?,?)",('Legacy mall','Ämne','Innehåll')); conn.commit(); conn.close()
            db=Database(path); self.assertEqual(db.get_contact(1)['name'],'Legacy'); self.assertEqual(db.templates(1)[0]['name'],'Legacy mall'); self.assertTrue(db.conn.execute("SELECT 1 FROM sqlite_master WHERE name='source_registry'").fetchone()); db.close()

if __name__=='__main__': unittest.main()
