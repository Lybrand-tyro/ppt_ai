import urllib.request
import json

print("测试 PPT AI 生成...")
print("=" * 60)

# 测试生成大纲
outline_data = {
    "topic": "人工智能的发展历程",
    "language": "zh",
    "use_llm": False
}

try:
    print("\n1. 生成大纲...")
    req = urllib.request.Request(
        "http://localhost:8001/api/generate-outline",
        data=json.dumps(outline_data).encode('utf-8'),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=30)
    outline = json.loads(resp.read().decode('utf-8'))
    print(f"   大纲标题: {outline.get('title')}")
    print(f"   幻灯片数量: {len(outline.get('slides', []))}")

    # 打印每张幻灯片的信息
    for i, slide in enumerate(outline.get('slides', []), 1):
        print(f"   [{i}] {slide.get('title')} ({slide.get('type')}) - 内容长度: {len(slide.get('content', ''))}")

    # 测试生成PPT
    print("\n2. 生成PPT...")
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
    print(f"   HTML长度: {len(html)}")

    # 检查HTML中的幻灯片数量
    slide_count = html.count('<div class="slide')
    print(f"   HTML中slide元素数量: {slide_count}")

    # 检查initSlides调用
    if 'initSlides(' in html:
        import re
        match = re.search(r'initSlides\((\d+)\)', html)
        if match:
            print(f"   initSlides参数: {match.group(1)}")

    print("\n✅ 测试成功!")

except Exception as e:
    print(f"\n❌ 测试失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()