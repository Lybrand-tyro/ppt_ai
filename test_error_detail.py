import urllib.request
import json
import sys

log_file = open('test_error_detail.txt', 'w', encoding='utf-8')

def log(msg):
    log_file.write(str(msg) + '\n')
    log_file.flush()

# Step 1: Generate outline
url = "http://localhost:8001/api/generate-outline"
data = json.dumps({"topic": "Test", "language": "zh", "use_llm": False}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

try:
    resp = urllib.request.urlopen(req, timeout=30)
    outline = json.loads(resp.read().decode('utf-8'))
    log("Step 1 SUCCESS: Outline = " + str(outline.get('title')))

    # Step 2: Generate PPT
    url2 = "http://localhost:8001/api/generate-slides"
    data2 = json.dumps({"outline": outline, "use_llm": False}).encode('utf-8')
    req2 = urllib.request.Request(url2, data=data2, headers={"Content-Type": "application/json"}, method="POST")

    resp2 = urllib.request.urlopen(req2, timeout=30)
    result = json.loads(resp2.read().decode('utf-8'))
    html = result.get('slides_html', '')
    log("Step 2 SUCCESS: PPT HTML = " + str(len(html)) + " chars")

except urllib.error.HTTPError as e:
    log("HTTP Error: " + str(e.code) + " " + str(e.reason))
    error_body = e.read().decode('utf-8')
    log("Error Response: " + error_body)
except Exception as e:
    log("ERROR: " + type(e).__name__ + " " + str(e))
    import traceback
    traceback.print_exc(file=log_file)

log_file.close()
print("Check test_error_detail.txt")