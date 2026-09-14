"""Download official GeoNames inputs and build the offline place database."""
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.request import urlopen
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_places import main

def download(url, dest):
    with urlopen(url, timeout=90) as response, dest.open("wb") as target:
        shutil.copyfileobj(response, target)

def run():
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "gunamilan/data/places.db")
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for name in ("IN", "cities15000"):
            archive = root / (name + ".zip")
            download("https://download.geonames.org/export/dump/" + name + ".zip", archive)
            with ZipFile(archive) as z:
                with z.open(name + ".txt") as source, (root / (name + ".txt")).open("wb") as target:
                    shutil.copyfileobj(source, target)
        download("https://download.geonames.org/export/dump/admin1CodesASCII.txt", root / "admin1.txt")
        main(str(root), str(output))
    print("Place search ready:", output)

if __name__ == "__main__":
    run()
