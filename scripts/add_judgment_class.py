with open('static/js/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

old_str = '<div class="card">\n            <div class="card-title accent">'
new_str = '<div class="card judgment-card">\n            <div class="card-title accent">'

if old_str in text:
    text = text.replace(old_str, new_str)
    with open('static/js/app.js', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Added judgment-card class successfully')
else:
    print('old_str not found')

