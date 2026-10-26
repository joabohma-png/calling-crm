@echo off
cd /d "%~dp0"
if not exist data mkdir data
py -m calling_crm --db "%~dp0data\calling_crm.sqlite3"
