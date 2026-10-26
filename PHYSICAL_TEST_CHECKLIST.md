# Fysisk sluttest

## Linux

- [ ] Starta från installerad katalog med `python3 -m calling_crm --db data/calling_crm.sqlite3`.
- [ ] Starta från USB med `./start-linux.sh`; kontrollera att databasen skapas under USB-mappens `data/`.
- [ ] Importera `examples/customers-fictional.csv` och kontrollera antal nya/uppdaterade/avvisade.
- [ ] Skapa profil, byt aktiv profil och verifiera att produkter, kunder och mallar inte blandas.
- [ ] Skapa/ändra erbjudande och kontrollera prisversion, deltagargränser och villkor.
- [ ] Registrera informationsmedgivande, öppna mejlgranskning och kontrollera till/från/ämne/innehåll.
- [ ] Kör ett testutskick mot testbrevlåda med STARTTLS. Kontrollera att lösenord aldrig sparas i databasen.
- [ ] Återkalla medgivande och kontrollera att granskningsvyn blockerar utskick.
- [ ] Registrera separat uppföljningsmedgivande och kontrollera fem kalenderdagar.
- [ ] Skapa krypterad backup, stäng programmet, återställ till kopia och verifiera kunddata.
- [ ] Kör `python3 -m calling_crm --diagnostics` med och utan Android ansluten.
- [ ] Med fysisk Android: acceptera ADB/RSA, kontrollera `devices`, starta uppringare och verifiera ljud manuellt.

## Windows 11

- [ ] Installera Python 3.12+ och Android Platform Tools vid behov.
- [ ] Kör `py -3 -m pip install -r requirements-build.txt` i byggmiljö.
- [ ] Kör `powershell -ExecutionPolicy Bypass -File .\build-windows.ps1`.
- [ ] Kopiera `dist\CallingCRM` till USB och starta `start-windows.cmd`.
- [ ] Upprepa import, profilbyte, erbjudande, medgivande, mejlgranskning, backup och återställning.
- [ ] Kontrollera Windows-brandvägg/localhost och att appen inte öppnas mot nätverket utan avsikt.
- [ ] Med fysisk Android: installera OEM-/ADB-drivrutin och upprepa telefonprovet.

## Godkännandekriterier

Utskicket får endast ske efter synligt medgivande, korrekt profil, korrekt mottagare och manuell bekräftelse. Ett fel i SMTP får inte skapa en skickad logg. Android utan verifierad ljudbrygga får inte beskrivas som ett genomfört headset-samtal.
