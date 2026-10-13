import json
import statistics
import os


path = os.path.join(os.path.dirname(__file__), "q-calculate-variance.json")
with open(path) as f:
    data = json.load(f)

print(len(data), data[:5])

varinace = statistics.variance(data)
print(round(varinace,2))