import urllib.request
import json
import sys

log_file = open('test_output.txt', 'w', encoding='utf-8')

def log(msg):
    log_file.write(msg + '\n')
    log_file.flush()

log("Starting test...")

# Step 1: Generate outline
url = "http://localhost:8001/api/generate-outline"
data = json.dumps({"topic": "Test", "language": "zh", "use_llm": False}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

try:
    log("Calling outline API...")
    resp = urllib.request.urlopen(req, timeout=30)
    outline = json.loads(resp.read().decode('utf-8'))
    log(f"Step 1 SUCCESS: Outline = {outline.get('title')}")
    sys.stdout.flush()

    # Step 2: Generate PPT
    log("Calling slides API...")
    url2 = "http://localhost:8001/api/generate-slides"
    data2 = json.dumps({"outline": outline, "use_llm": False}).encode('utf-8')
    req2 = urllib.request.Request(url2, data=data2, headers={"Content-Type": "application/json"}, method="POST")

    resp2 = urllib.request.urlopen(req2, timeout=30)
    result = json.loads(resp2.read().decode('utf-8'))
    html = result.get('slides_html', '')
    log(f"Step 2 SUCCESS: PPT HTML = {len(html)} chars")

except Exception as e:
    log(f"ERROR: {type(e).__name__} {str(e)}")
    import traceback
    traceback.print_exc(file=log_file)

log_file.close()
print("Test completed. Check test_output.txt")