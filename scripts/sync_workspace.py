# Workspace-to-repo sync script (safer keywords)
# Usage: set GH_KEY, TARGET_OWNER and TARGET_REPO env vars, then run.

import os
import base64
import requests

GITHUB_API = "https://api.github.com"
GH_KEY = os.environ.get("GH_KEY")
TARGET_OWNER = os.environ.get("TARGET_OWNER")
TARGET_REPO = os.environ.get("TARGET_REPO")

HEADERS = {"Authorization": f"Bearer {GH_KEY}", "Accept": "application/vnd.github.v3+json"}

IGNORED_DIRS = {".git", "venv", "__pycache__"}
IGNORED_FILES = {".DS_Store", "thumbs.db"}


def list_workspace_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for fname in filenames:
            if fname in IGNORED_FILES:
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            yield rel.replace('\\', '/')


def get_file_sha(owner, repo, path):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json().get("sha")
    return None


def put_file(owner, repo, path, content, message):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    b64 = base64.b64encode(content).decode('utf-8')
    payload = {"message": message, "content": b64}
    sha = get_file_sha(owner, repo, path)
    if sha:
        payload["sha"] = sha
    r = requests.put(url, json=payload, headers=HEADERS)
    return r


if __name__ == '__main__':
    root = os.getcwd()
    if not GH_KEY or not TARGET_OWNER or not TARGET_REPO:
        print("Please set GH_KEY, TARGET_OWNER and TARGET_REPO environment variables.")
        raise SystemExit(1)

    failed = []
    for path in list_workspace_files(root):
        try:
            with open(path, 'rb') as f:
                content = f.read()
            print(f"Uploading {path}...")
            r = put_file(TARGET_OWNER, TARGET_REPO, path, content, f"Sync: {path}")
            if not (200 <= r.status_code < 300):
                print(f"Failed {path}: {r.status_code} {r.text}")
                failed.append(path)
        except Exception as e:
            print(f"Error reading {path}: {e}")
            failed.append(path)

    if failed:
        print("Some files failed to upload:")
        for p in failed:
            print(" - ", p)
    else:
        print("Sync completed successfully.")
