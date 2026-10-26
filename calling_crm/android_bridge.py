from __future__ import annotations

import shutil
import subprocess
import platform
from urllib.parse import quote

class AdbBridge:
    name = "ADB / Android USB"
    def __init__(self, adb_path=None): self.adb = adb_path or shutil.which("adb") or "adb"
    def available(self): return shutil.which(self.adb) is not None
    def detect_device(self): return self.devices()
    def devices(self):
        if not self.available(): return []
        r=subprocess.run([self.adb,"devices"],capture_output=True,text=True,timeout=10,check=False)
        return [line.split("\t",1)[0] for line in r.stdout.splitlines()[1:] if "\tdevice" in line]
    def get_capabilities(self):
        return {"adb":self.available(),"devices":self.devices(),"dial":self.available(),"audio":False,"call_status":False,"note":"ADB startar uppringaren. Tvåvägsljud och säker samtalsstatus kräver en separat testad ljudbrygga/Bluetooth HFP."}
    def initiate_call(self, number, device=None):
        if not self.devices(): raise RuntimeError("Ingen godkänd Android-enhet hittades via ADB")
        args=[self.adb]+(["-s",device] if device else [])+["shell","am","start","-a","android.intent.action.DIAL","-d",f"tel:{quote(number)}"]
        r=subprocess.run(args,capture_output=True,text=True,timeout=15,check=False)
        if r.returncode: raise RuntimeError(r.stderr.strip() or "ADB kunde inte starta uppringaren")
        return {"status":"dialer_opened","stdout":r.stdout.strip()}
    dial = initiate_call
    def get_call_status(self): return {"status":"unknown","confirmed":False,"reason":"ADB-adaptern kan inte bekräfta aktivt mobilnätsamtal."}
    def end_call(self): raise RuntimeError("Att avsluta mobilnätsamtal via ADB är inte verifierat och lämnas till telefonen.")
    def check_audio_route(self): return {"available":False,"route":"unknown","reason":"USB-ljud för mobilnätsamtal är inte tillgängligt via ADB ensam."}
    def diagnostics(self):
        audio_commands=[x for x in ("wpctl","pactl","pw-cli") if shutil.which(x)]
        audio={"tools":audio_commands,"microphone":"unknown","speaker":"unknown","bridge":"not verified"}
        if audio_commands:
            tool=audio_commands[0]
            try:
                r=subprocess.run([tool,"status"] if tool=="wpctl" else [tool,"info"],capture_output=True,text=True,timeout=5,check=False)
                audio["command_status"]="available" if r.returncode==0 else "error"
                audio["summary"]=(r.stdout or r.stderr).strip()[:500]
            except OSError as exc: audio["command_status"]=f"error: {exc}"
        return {"platform":platform.system(),"adb_installed":self.available(),"android_devices":self.devices(),"call_control":"available" if self.available() else "unavailable","call_status":"not verified","audio_route":self.check_audio_route(),"audio":audio,"warning":"Fysisk Android-enhet, ljudbrygga och headset måste testas manuellt. ADB ensam ger inte tvåvägsljud."}
