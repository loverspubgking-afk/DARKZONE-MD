"""
deploy_hf.py  —  Hugging Face Spaces par automatic deploy
==========================================================
Ek token se poora agent deploy ho jata hai.
Permanent URL: https://huggingface.co/spaces/{USER}/{SPACE}

Usage:
  python3 deploy_hf.py
  (TOKEN aur SPACE naam environment variable ya prompt se lega)
"""

import os
import sys
from huggingface_hub import HfApi, create_repo

# Kaunsi files upload karni hain
FILES = [
    "app.py",
    "agent.py",
    "tools.py",
    "notrack_client.py",
    "requirements.txt",
    "Dockerfile",
    "README.md",
]

# HF Spaces ke liye README metadata (Docker space banana)
def make_space_readme(space_name):
    return f"""---
title: {space_name}
emoji: 🤖
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# NoTrack Agent

Uncensored autonomous AI agent with web search, tools & browser.
"""


def main():
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        token = input("Apna Hugging Face token paste karein (hf_xxx...): ").strip()

    space_name = os.environ.get("HF_SPACE_NAME", "notrack-agent")
    username = None

    api = HfApi(token=token)
    try:
        who = api.whoami()
        username = who["name"]
        print(f"✅ Logged in as: {username}")
    except Exception as e:
        print(f"❌ Token galat ya invalid: {e}")
        sys.exit(1)

    repo_id = f"{username}/{space_name}"
    print(f"🚀 Space create ho raha hai: {repo_id} ...")

    # repo/space banao (agar pehle se hai to overwrite ok)
    create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker",
                token=token, exist_ok=True, private=False)

    # space README (metadata)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(make_space_readme(space_name))
    FILES.append("README.md")

    # saari files upload
    base = os.path.dirname(os.path.abspath(__file__))
    for fname in FILES:
        fpath = os.path.join(base, fname)
        if os.path.exists(fpath):
            api.upload_file(path_or_fileobj=fpath, path_in_repo=fname,
                            repo_id=repo_id, repo_type="space", token=token)
            print(f"   ✅ uploaded {fname}")

    url = f"https://huggingface.co/spaces/{repo_id}"
    live = f"https://{username}-{space_name}.hf.space"
    print("\n" + "=" * 55)
    print("🎉 DEPLOY HO GAYA!")
    print("=" * 55)
    print(f"📁 Space:  {url}")
    print(f"🌐 LIVE:   {live}")
    print("(pehli baar build 2-4 minute lagta hai, phir hamesha chalta hai)")
    print("=" * 55)


if __name__ == "__main__":
    main()
