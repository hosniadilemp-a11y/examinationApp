import urllib.request
import tarfile
import os
import json

def download_pyodide():
    dest = os.path.join("frontend", "vendor", "pyodide")
    os.makedirs(dest, exist_ok=True)
    
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request("https://api.github.com/repos/pyodide/pyodide/releases/latest", headers=headers)
    data = json.loads(urllib.request.urlopen(req).read())
    
    asset = [a for a in data["assets"] if "pyodide-core" in a["name"]][0]
    download_url = asset["browser_download_url"]
    print(f"Téléchargement de Pyodide Core depuis {download_url} ({asset['size']} octets)...")
    
    tar_path = os.path.join(dest, "core.tar.bz2")
    urllib.request.urlretrieve(download_url, tar_path)
    print("Extraction de l'archive...")
    with tarfile.open(tar_path, "r:bz2") as tar:
        tar.extractall(path=dest)
    os.remove(tar_path)
    
    # Si les fichiers sont dans un sous-dossier, les remonter
    entries = os.listdir(dest)
    print("Contenu extrait dans vendor/pyodide :", entries)
    for entry in entries:
        sub = os.path.join(dest, entry)
        if os.path.isdir(sub) and "pyodide" in entry.lower():
            for f in os.listdir(sub):
                target = os.path.join(dest, f)
                if not os.path.exists(target):
                    os.rename(os.path.join(sub, f), target)
    print("Pyodide est prêt et embarqué localement pour fonctionnement 100% hors-ligne.")

if __name__ == "__main__":
    download_pyodide()
