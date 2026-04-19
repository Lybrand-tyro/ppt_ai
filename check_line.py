# Check the CSS line directly in the source file
with open('src/ppt_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line 275
if len(lines) >= 275:
    line_275 = lines[274]  # 0-indexed
    print("Line 275:", repr(line_275))

    if ".slide.active { display:" in line_275:
        print("ERROR: Single braces found!")
    elif ".slide.active {{ display:" in line_275:
        print("SUCCESS: Double braces found!")
    else:
        print("WARNING: Unexpected content")