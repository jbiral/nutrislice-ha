import json
from datetime import datetime

# Simulate state attributes
attributes = {
    "days": [
        {"date": "2026-02-19", "has_menu": True, "menu_items": [{"name": "Pizza", "category": "entree"}]},
        {"date": "2026-02-20", "has_menu": True, "menu_items": [{"name": "Burger", "category": "entree"}]},
    ]
}

# The user is navigating days. Let's trace back exactly what the JS does.
# SCENARIO: User clicks "Next" from today (Feb 19th) to tomorrow (Feb 20th)

current_js_date = datetime(2026, 2, 20)

yyyy = current_js_date.year
# JS getMonth is 0-indexed, but python's is 1-indexed. We simulate the JS math:
# mm = String(this.currentDate.getMonth() + 1).padStart(2, '0');
mm = str(current_js_date.month).zfill(2)
dd = str(current_js_date.day).zfill(2)

targetDateStr = f"{yyyy}-{mm}-{dd}"
print(f"Javascript generated target Date: {targetDateStr}")

found = False
for d in attributes["days"]:
    if d["date"] == targetDateStr:
        print(f"FOUND MENU DATA FOR {targetDateStr}: {d['menu_items']}")
        found = True

if not found:
    print("FAILED TO FIND DATA.")
