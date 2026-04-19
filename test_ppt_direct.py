import sys
sys.path.insert(0, 'src')

from ppt_service import PPTService
import json

print("直接测试 PPT Service...")
print("=" * 60)

ppt_service = PPTService()

# 创建一个测试大纲
outline = {
    "title": "人工智能的发展历程",
    "slides": [
        {"id": 1, "type": "title", "title": "人工智能的发展历程", "subtitle": "AI Evolution", "content": ""},
        {"id": 2, "type": "agenda", "title": "目录", "subtitle": "", "content": "1. 引言\n2. 核心技术\n3. 发展历程\n4. 应用场景\n5. 未来展望"},
        {"id": 3, "type": "content", "title": "引言", "subtitle": "", "content": "人工智能的定义\n机器学习的概念\n深度学习的突破"},
        {"id": 4, "type": "content", "title": "核心技术", "subtitle": "", "content": "神经网络架构\n自然语言处理\n计算机视觉"},
        {"id": 5, "type": "content", "title": "发展历程", "subtitle": "", "content": "1950年代：起步阶段\n1980年代：专家系统\n2010年代：深度学习"},
        {"id": 6, "type": "content", "title": "应用场景", "subtitle": "", "content": "智能语音助手\n自动驾驶汽车\n医疗诊断辅助"},
        {"id": 7, "type": "thankyou", "title": "谢谢", "subtitle": "感谢您的聆听", "content": ""}
    ],
    "metadata": {"language": "zh", "total_slides": 7}
}

print(f"大纲包含 {len(outline['slides'])} 张幻灯片")

import asyncio
async def test():
    print("\n生成HTML...")
    html = await ppt_service.generate_html(outline, "general", False)
    print(f"HTML长度: {len(html)}")

    # 检查幻灯片数量
    slide_count = html.count('<div class="slide')
    print(f"HTML中slide元素数量: {slide_count}")

    # 检查CSS样式
    if '.slide {' in html:
        print("✅ 找到 .slide CSS样式")
    else:
        print("❌ 未找到 .slide CSS样式")

    # 检查导航按钮
    if 'prevBtn' in html and 'nextBtn' in html:
        print("✅ 找到导航按钮")
    else:
        print("❌ 未找到导航按钮")

    # 检查initSlides
    if 'initSlides(' in html:
        print("✅ 找到initSlides调用")
    else:
        print("❌ 未找到initSlides调用")

    # 打印幻灯片的一部分HTML
    print("\n幻灯片HTML片段:")
    for i in range(1, 8):
        if f'<div class="slide' in html:
            start = html.find('<div class="slide')
            end = html.find('</div>', start) + 6
            print(f"  幻灯片1: {html[start:start+100]}...")
            break

asyncio.run(test())