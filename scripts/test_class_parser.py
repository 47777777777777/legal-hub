import gzip
import sys
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def test_class_based_parsing(gz_path):
    with gzip.open(gz_path, "rt", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    results = []
    # Find all table blocks
    # Each article usually has font class="artino"
    art_fonts = soup.find_all("font", class_="artino")
    print(f"{gz_path}: found {len(art_fonts)} articles")
    for af in art_fonts[:3]:
        print(f"  Art: {af.get_text(strip=True)}")

test_class_based_parsing("data/raw/lis/gz/A0040012.html.gz")
test_class_based_parsing("data/raw/lis/gz/B0000005.html.gz")

