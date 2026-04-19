import sys
sys.path.insert(0, 'src')

from ppt_service import PPTService

print("Testing CSS generation...")

ppt = PPTService()
config = ppt.scenario_configs["general"]

try:
    css = ppt._generate_css_styles(config)
    print("CSS generated successfully!")
    print("CSS length:", len(css))

    # Check for the problematic line
    if ".slide.active { display:" in css:
        print("ERROR: Found single braces!")
    elif ".slide.active {{ display:" in css:
        print("SUCCESS: Found double braces!")

    # Print the problematic section
    if ".slide.active" in css:
        idx = css.find(".slide.active")
        print("\nRelevant CSS section:")
        print(css[idx:idx+50])

except Exception as e:
    print("ERROR:", type(e).__name__, str(e))
    import traceback
    traceback.print_exc()