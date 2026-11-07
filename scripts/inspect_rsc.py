import os
import re
import json

raw_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'lawplayer', 'civil_procedure_code')
rsc_path = os.path.join(raw_dir, 'civil_art_2.rsc.txt')

with open(rsc_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Look for keyword "適用習慣之限制"
pos = text.find("適用習慣之限制")
print(f"Found '適用習慣之限制' at index {pos}")
if pos != -1:
    print("Context around title:")
    print(text[max(0, pos-200):min(len(text), pos+400)])

# Look for "10503501700"
pos2 = text.find("10503501700")
print(f"\nFound '10503501700' at index {pos2}")
if pos2 != -1:
    print("Context around interpretation:")
    print(text[max(0, pos2-200):min(len(text), pos2+400)])

