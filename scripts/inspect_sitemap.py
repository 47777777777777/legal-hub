import xml.etree.ElementTree as ET

tree = ET.parse("data/raw/lawplayer/act-1-sitemap.xml")
root = tree.getroot()
print("Root tag:", root.tag)
urls = []
for child in root:
    loc = child.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
    if loc is not None and loc.text:
        urls.append(loc.text)

print(f"Total urls in act-1-sitemap.xml: {len(urls)}")
print("First 10 urls:")
for u in urls[:10]:
    print(" ", u)

