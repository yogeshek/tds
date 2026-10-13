import csv, io, zipfile

ZIP = r"D:\projects\TDS\data\q-unicode-data.zip"
TARGETS = {"\u2122", "\u201a", "\u0160"}  # ™  ‚ (low quote, not a comma)  Š
FILES = [("data1.csv", "cp1252", ","), ("data2.csv", "utf-8", ","), ("data3.txt", "utf-16", "\t")]

total = 0
with zipfile.ZipFile(ZIP) as z:
    for name, enc, sep in FILES:
        text = z.read(name).decode(enc)
        rows = list(csv.reader(io.StringIO(text), delimiter=sep))
        total += sum(float(v) for s, v in rows[1:] if s in TARGETS)

print(total)
