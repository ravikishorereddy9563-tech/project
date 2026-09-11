"""Create the 160-row golden-set template from hand-authored utterance families."""
from __future__ import annotations
import csv
from pathlib import Path

FAMILIES = {
"battery_or_performance": ("My iPhone battery is draining quickly", "Please check Battery Health in Settings > Battery and update iOS. If it continues, contact us by DM.", 10, 0),
"purchase_or_duplicate_charge": ("I was charged twice for an App Store purchase", "We can look into duplicate charges in a private message. Please send the order details via DM.", 10, 1),
"device_or_accessory_setup": ("My AirPods will not connect to my iPhone", "Reset the AirPods, make sure Bluetooth is on, and pair them again. DM us if that does not help.", 10, 0),
"account_access": ("I forgot my Apple ID password", "You can reset it at iforgot.apple.com. We can help further in DM if needed.", 10, 0),
"order_or_delivery": ("My order has not arrived and tracking stopped updating", "Please send the order number in a DM so we can check the delivery status.", 10, 1),
"repair_or_damage": ("The screen on my iPhone is cracked", "Repair options and pricing are available at support.apple.com/repair. Please DM if you need help finding a provider.", 10, 1),
"payments": ("Apple Pay was declined when I tried to pay", "Check that your billing address and card details are current, then contact your bank if the issue continues.", 10, 1),
"storage_or_cloud": ("My iCloud storage is full", "Review large backups and photos in iCloud settings, or choose a larger storage plan if needed.", 10, 0),
"trade_in": ("Where is my trade-in credit?", "Trade-in status can be checked at apple.com/shop/trade-in/status. DM the confirmation number if it is missing.", 10, 1),
"account_access": ("My account is locked after too many attempts", "Account recovery is available at iforgot.apple.com. Please do not share your password here.", 10, 0),
"other_or_unknown": ("I need help with a problem I cannot describe", "I want to make sure we route this correctly. Please send the product and issue details in a DM.", 60, 1),
}

rows = []
for intent, (base, reference, count, escalate) in FAMILIES.items():
    for index in range(count):
        suffix = ["", " please", " today", " urgently", " after the update"][index % 5]
        rows.append({"id": f"golden-{len(rows)+1:03d}", "text": base + suffix, "intent": intent,
                     "escalate": escalate, "reference_reply": reference})
Path("data").mkdir(exist_ok=True)
with Path("data/golden.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
    writer.writeheader(); writer.writerows(rows)
print(f"wrote {len(rows)} golden rows")
