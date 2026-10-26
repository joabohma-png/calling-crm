# Calling CRM

En lokal, produktoberoende calling-plattform för Linux och Windows 11. Den körs offline med SQLite och en enkel webbaserad lokal arbetsyta som inte kräver externa Python-paket.

## Start

```bash
python3 -m calling_crm --db calling_crm.sqlite3
```

Öppna `http://127.0.0.1:8787`. Startscript finns i `start-linux.sh` och `start-windows.cmd`.

## Funktioner i denna version

- förenklad arbetsyta med exakt tre huvudflikar: Ring, Offert och Utskick
- kundkort med snabb Ring/Spara/Ändra/Kasta, mjuk arkivering, anteckningar och tidsstämplad historik
- tydliga statuslägen för ej ringd, kontaktad, lead, uppföljning, bokad och avslutad
- uppföljningskö med separata räknare för idag och försenade återkontakter
- Decimal-baserad SEK-kalkyl med redigerbart slutpris, valbara kostnadsposter och 25 % redigerbar moms
- versionssparade kundofferter med redigerbar platshållarmall och PDF-förhandsgranskning
- vanligt mejl via `mailto:` utan offert samt offertmejl via SMTP med valfri PDF-bilaga
- mejlstatus skiljer på öppnat, användarbekräftat och tekniskt skickat

- arbetsprofil med konfigurerbar uppföljningsintervall
- kundkort och sökning
- CSV/XLSX-import med svensk/engelsk kolumnidentifiering, telefonnormalisering och importstatistik
- importbatcher och ångra-API i datalagret
- GDPR-spärr: importerade kontakter får inte samtycke automatiskt; opt-out och samtyckeshändelser sparas
- samtal via befintlig ADB/ACTION_DIAL-väg och separat adaptergränssnitt
- manuell samtalsregistrering med status och anteckning
- uppföljningskö och klarmarkering
- lokal SQLite-databas med profiler, produkter, erbjudanden, mallar och sändningslogg som datamodell
- mejlgranskningsvy med aktuell mottagare, avsändare, ämne och renderat innehåll
- SMTP STARTTLS/SSL med lösenord endast i minnet och aldrig i databasen
- krypterad backup/återställning via OpenSSL AES-256-CBC/PBKDF2
- valfritt grundläggande HTTP Basic-skydd via `CALLING_CRM_ACCESS_TOKEN`
- telefondiagnostik via `python3 -m calling_crm --diagnostics` eller `/diagnostics`
- källregister med filtyp, filnamn, sökvägar, importbatch, arbetsprofil, SHA-256 och källversion
- källhänvisning på kundkort med saknad fil-detektering och hashkontrollerad ompekning

## Telefonläge och begränsning

`AdbBridge` återanvänder den fungerande implementationen och exponerar `detect_device`, `initiate_call`, `get_call_status`, `end_call`, `check_audio_route` och `get_capabilities`. ADB kan starta telefonens uppringare men ger inte i sig tvåvägsljud via datorns headset eller verifierad mobilnätsstatus. Därför loggas inte ett samtal som genomfört förrän användaren registrerar resultatet. Full ljudbrygga kräver separat tekniskt verifierad Bluetooth HFP/USB-lösning på den aktuella telefonmodellen.

## Profil- och produktdata

Datamodellen stödjer produkter, versionsbara erbjudanden, pris/villkor och mejlmallar per profil. Den första profilen skapas som `Standardprofil`; användaren kan skapa fler via Profil. Inga påhittade priser eller HLR-villkor har hårdkodats.

## Juridiska antaganden

Detta är ett tekniskt stöd, inte juridisk rådgivning. Före produktion måste personuppgiftsansvarig, ändamål, rättslig grund, gallring, behörighet, NIX/telefonregler, marknadsföringsregler och samtyckestext verifieras för den faktiska verksamheten. Informationsgodkännande, fortsatt marknadsföring och avregistrering behandlas som separata tillstånd i datamodellen.

## Tester

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile calling_crm/*.py
```

Starta med åtkomstskydd:

```bash
CALLING_CRM_ACCESS_TOKEN='ett-lokalt-token' python3 -m calling_crm
```

Testdata utan verkliga personuppgifter finns i `examples/customers-fictional.csv`. HTTP-gränssnittet har verifierats lokalt genom riktiga HTTP-anrop till startsida, erbjudandevy, inställningar, kundkort och mejlgranskning. SMTP med riktig leverantör, Android-ljud och Windows-binär kräver extern miljö/utrustning och är inte falskt markerade som verifierade.

## Källhänvisningar

Varje filimport registreras i `source_registry` och kopplas via `contact_sources` till importerade kundkort. SHA-256 används för att undvika dubbla källposter och för att kontrollera en ny filplats. Uploadade filer kopieras till databaskatalogens `sources/` och får en relativ sökväg, vilket gör portabel drift möjlig även när ursprunglig sökväg inte längre finns. Produkt- och erbjudandekällor kan länkas via `product_sources` och `offer_sources` när pris/villkor importeras från externa dokument.

## Windows och paketering

Windows byggs i Windows 11 med `py -3 -m pip install -r requirements-build.txt` följt av `powershell -ExecutionPolicy Bypass -File .\build-windows.ps1`. Linux använder motsvarande `./build-linux.sh` efter installation av PyInstaller. Denna Linux-miljö saknar PyInstaller och Windows, så inga Windows-tester eller Windows-binärer är påstådda som genomförda.
