import os
import requests
import yaml
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Settings ---
INPUT_FILE = "videos.yaml"           # state: [video urls]
OUTPUT_DIR = "backgrounds"           # copy this folder to <config>/www/
URL_PREFIX = "/local/backgrounds/"   # where Home Assistant serves OUTPUT_DIR
MAX_WORKERS = 6                      # number of concurrent downloads

# --- Helpers ---
def download_file(url, filename):
    """Download a single file with progress bar."""
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        with open(filename, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=os.path.basename(filename), leave=False
        ) as pbar:
            for chunk in r.iter_content(1024 * 32):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        return f"✅ {filename}"
    except Exception as e:
        return f"❌ {filename} failed: {e}"

# --- Main ---
def main():
    # Load YAML file
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tasks = []
    state_url = {}

    # Build download list with renamed filenames. A link listed twice in one
    # state is downloaded once but kept twice in state_url, so it still plays
    # twice as often.
    for category, urls in data.items():
        files = {}
        state_url[category] = []
        for url in urls:
            if url not in files:
                files[url] = f"{category}{len(files) + 1}.mp4"
                fullpath = os.path.join(OUTPUT_DIR, files[url])
                if not os.path.exists(fullpath):
                    tasks.append((url, fullpath))
            state_url[category].append(URL_PREFIX + files[url])

    # Download concurrently
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(download_file, url, path) for url, path in tasks]
        for fut in as_completed(futures):
            print(fut.result())

    print(f"\n✅ All downloads complete! Files saved in: {OUTPUT_DIR}")
    print("Copy that folder to <config>/www/ and use this in your animated_background config:\n")
    print(yaml.safe_dump({"state_url": state_url}, sort_keys=False))

if __name__ == "__main__":
    main()
