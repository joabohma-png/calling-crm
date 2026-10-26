import tempfile
import unittest
import zipfile
from pathlib import Path

from calling_crm.db import Database
from calling_crm.importer import STANDARD_V1_COLUMNS, preview, read_contacts, read_standard_v1

class StandardImportTests(unittest.TestCase):
    def make_xlsx(self,path):
        values=list(STANDARD_V1_COLUMNS)+['Test AB','Anna Test','070-123 45 67','anna@example.test','Testgatan 1','12345','Teststad','SE','fiktiv','Tjänst','Nej','Nej']
        def cell(index,value):
            column=chr(65+index); return f'<c r="{column}1" t="inlineStr"><is><t>{value}</t></is></c>' if index<12 else f'<c r="{column}2" t="inlineStr"><is><t>{value}</t></is></c>'
        header=''.join(cell(i,v) for i,v in enumerate(STANDARD_V1_COLUMNS)); row=''.join(f'<c r="{chr(65+i)}2" t="inlineStr"><is><t>{v}</t></is></c>' for i,v in enumerate(values[12:]))
        sheet=f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1">{header}</row><row r="2">{row}</row></sheetData></worksheet>'
        with zipfile.ZipFile(path,'w') as z: z.writestr('xl/worksheets/sheet1.xml',sheet)

    def test_standard_xlsx_to_customer_and_source_registry(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); xlsx=root/'customers.xlsx'; self.make_xlsx(xlsx); rows=list(read_standard_v1(xlsx)); self.assertEqual(rows[0]['company'],'Test AB'); self.assertEqual(rows[0]['phone'],'0701234567')
            db=Database(root/'crm.db'); pid=db.profiles()[0]['id']; sid=db.register_source(pid,'excel',xlsx.name,str(xlsx),source_version='Calling CRM v1.0'); cid,_=db.upsert_contact(rows[0],pid); db.link_contact_source(cid,sid); batch=db.import_batch(pid,xlsx.name,[cid],sid)
            self.assertEqual(db.get_contact(cid)['company'],'Test AB'); self.assertEqual(db.sources_for_contact(cid)[0]['source_version'],'Calling CRM v1.0'); self.assertEqual(db.source(sid)['import_batch_id'],batch); self.assertFalse(db.eligible_for_information(cid)); db.close()

    def test_standard_headers_are_strict_and_legacy_remains_separate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'wrong.csv'; p.write_text('Namn,Telefon\nTest,0700\n',encoding='utf-8')
            with self.assertRaises(ValueError): list(read_standard_v1(p))

    def test_flexible_import_supports_reordered_extra_and_missing_columns(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'real-list.csv'; p.write_text('Kommentar;Kund;Telefonnummer;Ort;Extra\nBehåll;Fiktiva AB;0700123456;Luleå;ignorera\n;Utan nummer;;Umeå;extra\n',encoding='utf-8')
            info=preview(p); self.assertEqual(info['mapping'][1],'company'); self.assertEqual(info['mapping'][2],'phone'); self.assertEqual(info['mapping'][3],'city')
            rows=list(read_contacts(p)); self.assertEqual(rows[0]['company'],'Fiktiva AB'); self.assertEqual(rows[0]['phone'],'0700123456'); self.assertEqual(rows[1]['city'],'Umeå'); self.assertEqual(rows[1]['phone'],'')

    def test_import_update_does_not_clear_existing_fields_with_blank_cells(self):
        with tempfile.TemporaryDirectory() as d:
            db=Database(Path(d)/'crm.db'); pid=db.profiles()[0]['id']; cid,_=db.upsert_contact({'company':'Fiktiva AB','name':'Anna','phone':'0700','notes':'Viktig historik'},pid); db.upsert_contact({'company':'Fiktiva AB','phone':'0700','name':'','notes':''},pid); row=db.get_contact(cid); self.assertEqual(row['name'],'Anna'); self.assertEqual(row['notes'],'Viktig historik'); db.close()

if __name__=='__main__': unittest.main()
