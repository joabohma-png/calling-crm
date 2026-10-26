# Portabel USB-struktur

```text
CallingCRM/
  app/                 # källkod eller PyInstaller-filer
  data/calling_crm.sqlite3
  data/sources/       # hanterade kopior av importerade källfiler
  start-linux.sh
  start-windows.cmd
```

Databasen ska ligga på USB-minnet och öppnas av endast en process åt gången. SQLite använder låsning och busy-timeout, men programmet får inte köras samtidigt från två datorer mot samma fil. Stäng programmet normalt före frånkoppling; avbryt aldrig USB-minnet under skrivning. Säkerhetskopiera `data/calling_crm.sqlite3` före större importer. En installerad version bör i stället använda användarens lokala datakatalog.

För Linux krävs Python 3.12+ (eller en paketerad körbar fil). För telefonfunktion krävs Android Platform Tools, USB-debugging, godkänd RSA-dialog och telefonens drivrutiner. ADB öppnar uppringaren; den här adaptern verifierar inte mobilnätsamtalets tvåvägsljud eller aktiva samtalsstatus.

Startarna använder relativa sökvägar från sin egen katalog. `data/`, backupfiler och eventuella lösenord ska inte versionshanteras; projektets `.gitignore` blockerar dessa mönster. Använd `--diagnostics` före fysisk telefonprovning.

Kundkort behåller sin data om en källfil flyttas eller saknas. Ange den nya filplatsen via kundkortets källhänvisning; CRM accepterar endast filen om SHA-256 matchar registrerad källa.
