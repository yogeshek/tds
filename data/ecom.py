import json

with open(r"D:\projects\TDS\data\ecom.json", encoding="utf-8") as f:
    products = json.load(f)
print(products)

filtered = [p for p in products if p["price"]>=87.94]

print(len(products), "->", len(filtered))

sorted_products = sorted(filtered, key=lambda p: (p["category"], -p["price"], p["name"]))

print(json.dumps(sorted_products))
