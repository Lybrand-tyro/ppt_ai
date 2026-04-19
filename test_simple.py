import urllib.request
import json

print("测试 PPT AI 生成...")

outline_data = {
    "topic": "人工智能",
    "language": "zh",
    "use_llm": False
}

try:
    print("1. 生成大纲...")
    req = urllib.request.Request(
        "http://localhost:8001/api/generate-outline",
        data=json.dumps(outline_data).encode('utf-8'),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=30)
    outline = json.loads(resp.read().decode('utf-8'))
    print(f"   成功: {len(outline.get('slides', []))} 张幻灯片")

    print("2. 生成PPT...")
    slides_data = {
        "outline": outline,
        "use_llm": False
    }
    req = urllib.request.Request(
        "http://localhost:8001/api/generate-slides",
        data=json.dumps(slides_data).encode('utf-8'),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read().decode('utf-8'))
    html = result.get('slides_html', '')
    print(f"   成功: {len(html)} 字符")

    print("\n✅ 全部成功!")

except Exception as e:
    print(f"\n❌ 失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()