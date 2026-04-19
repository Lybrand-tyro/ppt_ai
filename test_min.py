import urllib.request
import json

url = "http://localhost:8001/api/generate-outline"
data = json.dumps({"topic": "Test", "language": "zh", "use_llm": False}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read().decode('utf-8'))
    print("SUCCESS: Outline =", result.get('title'))
except Exception as e:
    print("ERROR:", e)