import urllib.request
import json

# Step 1: Generate outline
url = "http://localhost:8001/api/generate-outline"
data = json.dumps({"topic": "Test", "language": "zh", "use_llm": False}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

try:
    resp = urllib.request.urlopen(req, timeout=30)
    outline = json.loads(resp.read().decode('utf-8'))
    print("Step 1 SUCCESS: Outline =", outline.get('title'))

    # Step 2: Generate PPT
    url2 = "http://localhost:8001/api/generate-slides"
    data2 = json.dumps({"outline": outline, "use_llm": False}).encode('utf-8')
    req2 = urllib.request.Request(url2, data=data2, headers={"Content-Type": "application/json"}, method="POST")

    resp2 = urllib.request.urlopen(req2, timeout=30)
    result = json.loads(resp2.read().decode('utf-8'))
    html = result.get('slides_html', '')
    print("Step 2 SUCCESS: PPT HTML =", len(html), "chars")

except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.reason)
    error_body = e.read().decode('utf-8')
    print("Error Response:", error_body)
except Exception as e:
    print("ERROR:", type(e).__name__, str(e))
    import traceback
    traceback.print_exc()