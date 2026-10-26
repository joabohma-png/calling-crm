from __future__ import annotations
import csv, re, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ALIASES={"company":{"company","company_name","företag","foretag","företagsnamn","kund","organisation","organization"},"name":{"name","contact_name","namn","kontakt","contact","kontaktperson"},"phone":{"phone","telefon","telefonnummer","mobil","mobile","tel"},"email":{"email","e-post","epost","mail"},"address":{"address","adress","gatuadress"},"postal_code":{"postal_code","postnummer","postnr","zip","zipcode"},"city":{"city","ort","stad"},"country":{"country","land"},"product":{"product","produkt","tjänst","tjanst","kampanj"},"notes":{"notes","anteckningar","note","kommentar","kommentarer","notering","noteringar"},"information_consent":{"information_consent","information consent","informationsmedgivande"},"consent_marketing":{"consent","samtycke","marketing_consent","marketing consent","marknadsföring","marknadsforing"}}
STANDARD_V1_COLUMNS=("company_name","contact_name","phone","email","address","postal_code","city","country","notes","product","information_consent","marketing_consent")
def _key(v): return re.sub(r"[\s_\-]","",str(v or "").strip().lower())
def si_tag(element): return element.tag.rsplit("}",1)[-1]
def normalize_phone(value):
    raw=str(value or "").strip(); prefix="+" if raw.startswith("+") else ""
    digits=re.sub(r"\D","",raw)
    if raw.startswith("00"): prefix="+"; digits=digits[2:]
    return prefix+digits if digits else ""
def _consent(v): return str(v or "").strip().lower() in {"1","true","yes","ja","j","x"}
def detect_mapping(headers, overrides=None):
    mapping={}; overrides=overrides or {}
    for i,h in enumerate(headers):
        if i in overrides: mapping[i]=overrides[i]; continue
        key=_key(h)
        for field,names in ALIASES.items():
            if key in {_key(n) for n in names}: mapping[i]=field; break
    return mapping
def mapping_choices(headers):
    return {i: sorted({field for field,names in ALIASES.items() if _key(h) == _key(n) for n in names}) for i,h in enumerate(headers)}
def map_rows(rows, overrides=None):
    headers=rows[0] if rows else []; mapping=detect_mapping(headers,overrides); overrides=overrides or {}
    for row_number,row in enumerate(rows[1:],2):
        d={}; row=list(row)+[""]*max(0,len(headers)-len(row))
        for i,value in enumerate(row[:len(headers)]):
            field=overrides.get(i,mapping.get(i))
            if not field: continue
            value="" if value is None else str(value).strip()
            if value and not d.get(field): d[field]=value
        d["phone"]=normalize_phone(d.get("phone")); d["consent_marketing"]=_consent(d.get("consent_marketing")); yield d
def read_csv_rows(path):
    with open(path,newline="",encoding="utf-8-sig") as f:
        sample=f.read(4096); f.seek(0)
        try:dialect=csv.Sniffer().sniff(sample,delimiters=",;\t")
        except csv.Error:dialect=csv.get_dialect("excel")
        return list(csv.reader(f,dialect))
def read_xlsx_rows(path):
    try:
        import openpyxl
        return [list(row) for row in openpyxl.load_workbook(path,read_only=True,data_only=True).active.iter_rows(values_only=True)]
    except ImportError: pass
    with zipfile.ZipFile(path) as z:
        shared=[]
        if "xl/sharedStrings.xml" in z.namelist():
            root=ET.fromstring(z.read("xl/sharedStrings.xml")); shared=["".join(t.text or "" for t in si.iter() if str(si_tag(t))=="t") for si in root.iter() if str(si_tag(si))=="si"]
        root=ET.fromstring(z.read("xl/worksheets/sheet1.xml")); rows=[]
        for row in (x for x in root.iter() if str(si_tag(x))=="row"):
            vals=[]; next_col=0
            for cell in (x for x in row.iter() if str(si_tag(x))=="c"):
                ref=cell.attrib.get("r", "")
                match=re.match(r"([A-Z]+)", ref)
                if match:
                    col=0
                    for letter in match.group(1): col=col*26+ord(letter)-64
                    col-=1
                    vals.extend([""]*max(0, col-next_col)); next_col=col
                v=next((x.text or "" for x in cell.iter() if str(si_tag(x))=="v"),"")
                if cell.attrib.get("t")=="inlineStr": v="".join(x.text or "" for x in cell.iter() if str(si_tag(x))=="t")
                if cell.attrib.get("t")=="s" and v.isdigit(): v=shared[int(v)]
                vals.append(v); next_col += 1
            rows.append(vals)
        return rows
def preview(path, overrides=None):
    rows=read_csv_rows(path) if Path(path).suffix.lower()==".csv" else read_xlsx_rows(path); return {"headers":rows[0] if rows else [],"mapping":detect_mapping(rows[0] if rows else [],overrides),"rows":[dict(x) for x in list(map_rows(rows,overrides))[:20]],"total_rows":max(0,len(rows)-1)}
def read_contacts(path, overrides=None):
    rows=read_csv_rows(path) if Path(path).suffix.lower()==".csv" else read_xlsx_rows(path); yield from map_rows(rows,overrides)

def validate_standard_v1(rows):
    headers=tuple(str(x or "") for x in (rows[0] if rows else ()))
    if headers != STANDARD_V1_COLUMNS:
        raise ValueError("Calling CRM v1.0 kräver exakt 12 fasta kolumner: " + ", ".join(STANDARD_V1_COLUMNS))
    if any(len(row)!=12 for row in rows[1:]): raise ValueError("Calling CRM v1.0 innehåller en rad med fel antal kolumner")

def read_standard_v1(path):
    rows=read_csv_rows(path) if Path(path).suffix.lower()==".csv" else read_xlsx_rows(path)
    validate_standard_v1(rows)
    for row in rows[1:]:
        d={"company":row[0],"name":row[1],"phone":normalize_phone(row[2]),"email":str(row[3] or "").strip().lower(),"address":row[4],"notes":row[8],"product":row[9],"information_consent":_consent(row[10]),"consent_marketing":_consent(row[11]),"consent_source":"import"}
        yield d
