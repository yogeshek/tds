import zipfile
from pathlib import Path

zip_path = Path(r"D:\projects\TDS\data\q-replace-across-files.zip")
out_dir = Path(r"D:\projects\TDS\data\q-replace-across-files")

out_dir.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(zip_path) as z:
    z.extractall(out_dir)
    
import re

for f in out_dir.rglob("*"):
    if f.is_file():
        data = f.read_bytes()
        f.write_bytes(re.sub(rb"iitm", b"IIT Madras", data, flags=re.IGNORECASE))
        
import hashlib

h = hashlib.sha256()
for f in sorted(p for p in out_dir.iterdir() if p.is_file()):
    h.update(f.read_bytes())
print(h.hexdigest())
