from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

columns=("company_name","contact_name","phone","email","address","postal_code","city","country","notes","product","information_consent","marketing_consent")
root=Path(__file__).resolve().parents[1]
target=root/'data'/'templates'/'calling_crm_v1.0.xlsx'
sheet=''.join(f'<c r="{chr(65+i)}1" t="inlineStr"><is><t>{column}</t></is></c>' for i,column in enumerate(columns))
xml=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1">{sheet}</row></sheetData></worksheet>'''
content_types='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'''
rels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'''
workbook='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Calling CRM v1.0" sheetId="1" r:id="rId1"/></sheets></workbook>'''
workbook_rels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'''
with ZipFile(target,'w',ZIP_DEFLATED) as archive:
    archive.writestr('[Content_Types].xml',content_types); archive.writestr('_rels/.rels',rels); archive.writestr('xl/workbook.xml',workbook); archive.writestr('xl/_rels/workbook.xml.rels',workbook_rels); archive.writestr('xl/worksheets/sheet1.xml',xml)
print(target)
