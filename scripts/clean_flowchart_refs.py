import re

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Remove flowchart-modal-close event listener
pattern1 = re.compile(r'\s*// Flowchart Modal Close\s*document\.getElementById\("flowchart-modal-close"\)\.addEventListener\("click", \(\) => \{\s*document\.getElementById\("flowchart-modal"\)\.classList\.add\("hidden"\);\s*\}\);', re.MULTILINE)
text = pattern1.sub('', text)

# 2. Remove document.getElementById("flowchart-modal").classList.add("hidden");
text = text.replace('document.getElementById("flowchart-modal").classList.add("hidden");\n        ', '')
text = text.replace('document.getElementById("flowchart-modal").classList.add("hidden");', '')

# 3. Remove Flowchart Fullscreen Trigger block
pattern3 = re.compile(r'\s*// Flowchart Fullscreen Trigger\s*root\.querySelectorAll\("\.flowchart-fullscreen-btn"\)\.forEach\(\(btn\) => \{[\s\S]*?\}\);\s*\}\);', re.MULTILINE)
text = pattern3.sub('', text)

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print('Cleaned flowchart modal refs successfully')

