#!/usr/bin/env python3
"""Demo script for Email Document Assistant"""
import sys
sys.path.insert(0, '/Users/akarnik/interactionInterview/interaction-challenge')

from src.server import _process_email_automation
import subprocess

print("=" * 60)
print("EMAIL DOCUMENT ASSISTANT - DEMO")
print("=" * 60)
print("\nProcessing: https://interaction.co/assets/easy-pdf.json\n")

result = _process_email_automation("https://interaction.co/assets/easy-pdf.json")

print("=" * 60)
if result["status"] == "success":
    print("✅ SUCCESS!")
    print("=" * 60)
    print(f"\nFilled PDF: {result['filled_pdf']}")
    print(f"Fields filled: {result['fields_filled']}")
    print(f"Subject: {result['email_subject']}")
    print(f"\nOpening PDF...\n")
    subprocess.run(["open", result['filled_pdf']])
else:
    print("❌ ERROR!")
    print("=" * 60)
    print(f"\n{result.get('message', 'Unknown error')}\n")
