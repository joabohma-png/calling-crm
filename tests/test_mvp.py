import tempfile
import unittest
import zipfile
from pathlib import Path

from calling_crm.db import Database
from calling_crm.importer import read_contacts, normalize_phone, preview


class MvpTests(unittest.TestCase):
    def test_import_and_consent_gate(self):
        with tempfile.TemporaryDirectory() as d:
            db = Database(Path(d) / 'test.db')
            cid, created = db.upsert_contact({'name':'Anna', 'email':'anna@example.test', 'consent_marketing':False})
            self.assertTrue(created)
            self.assertFalse(db.eligible_for_marketing(cid))
            db.upsert_contact({'name':'Anna', 'email':'anna@example.test', 'consent_marketing':True})
            self.assertTrue(db.eligible_for_marketing(cid))
            db.upsert_contact({'name':'Anna uppdaterad', 'email':'anna@example.test'})
            self.assertTrue(db.eligible_for_marketing(cid))
            db.set_opt_out(cid)
            self.assertFalse(db.eligible_for_marketing(cid))
            db.close()

    def test_csv_aliases(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'contacts.csv'; p.write_text('Namn;Telefon;E-post;Samtycke\nBo;0700;bo@example.test;Ja\n', encoding='utf-8')
            rows = list(read_contacts(p))
            self.assertEqual(rows[0]['name'], 'Bo')
            self.assertTrue(rows[0]['consent_marketing'])

    def test_profile_followup_and_call_queue(self):
        with tempfile.TemporaryDirectory() as d:
            db = Database(Path(d) / 'test.db')
            pid = db.profiles()[0]['id']
            cid, _ = db.upsert_contact({'name': 'Fiktiv', 'phone': '070-123 45 67'}, pid)
            db.log_call(cid, 'manual', 'information', 'Skicka information')
            self.assertEqual(db.get_contact(cid)['status'], 'information')
            db.create_followup(cid)
            self.assertEqual(len(db.followups(pid)), 1)
            self.assertEqual(db.queue_counts(pid)['new'], 0)
            db.close()

    def test_import_never_grants_consent_and_phone_normalizes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'contacts.csv'
            p.write_text('Företag;Namn;Telefon;E-post;Samtycke\nTest AB;Test;0046 70-123 45 67;test@example.test;Ja\n', encoding='utf-8')
            rows = list(read_contacts(p))
            self.assertEqual(rows[0]['phone'], '+46701234567')
            db = Database(Path(d) / 'test.db')
            rows[0]['consent_source'] = 'import'
            cid, _ = db.upsert_contact(rows[0], db.profiles()[0]['id'])
            self.assertFalse(db.eligible_for_marketing(cid))
            self.assertEqual(normalize_phone('+46 (0)70-123 45 67'), '+460701234567')
            db.close()

    def test_xlsx_import_without_openpyxl(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'contacts.xlsx'
            workbook='''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'''
            sheet='''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Namn</t></is></c><c r="B1" t="inlineStr"><is><t>Telefon</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>Test</t></is></c><c r="B2" t="inlineStr"><is><t>070-123</t></is></c></row></sheetData></worksheet>'''
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('xl/worksheets/sheet1.xml',sheet)
            rows=list(read_contacts(p)); self.assertEqual(rows[0]['name'],'Test'); self.assertEqual(rows[0]['phone'],'070123')


if __name__ == '__main__':
    unittest.main()
