import urllib.request
import json
import sys

try:
    # Test outline
    data = {"topic": "Test", "language": "zh", "use_llm": False}
    req = urllib.request.Request(
        "http://localhost:8001/api/generate-outline",
        data=json.dumps(data).encode('utf-8'),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=30)
    outline = json.loads(resp.read().decode('utf-8'))
    print(f"[OK] Outline generated: {outline.get('title')}")

    # Test PPT
    slides_data = {"outline": outline, "use_llm": False}
    req = urllib.request.Request(
        "http://localhost:8001/api/generate-slides",
        data=json.dumps(slides_data).encode('utf-8'),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read().decode('utf-8'))
    html = result.get('slides_html', '')
    print(f"[OK] PPT generated: {len(html)} chars")

except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)