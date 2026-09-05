#!/usr/bin/env python3
"""RED-MIND backend keepalive — GitHub Actions se chalta hai (har 8 ghante).
Secrets (env): KAGGLE_USERNAME, KAGGLE_KEY, GH_TOKEN
Token repo file mein NAHI hai — runtime pe env se aata hai.
"""
import json, os, subprocess, sys

GH_TOKEN = os.environ.get("GH_TOKEN", "")
KU = os.environ.get("KAGGLE_USERNAME", "")
KK = os.environ.get("KAGGLE_KEY", "")
if not (GH_TOKEN and KU and KK):
    sys.exit("env secrets missing")

kd = os.path.expanduser("~/.kaggle")
os.makedirs(kd, exist_ok=True)
json.dump({"username": KU, "key": KK}, open(kd + "/kaggle.json", "w"))
os.chmod(kd + "/kaggle.json", 0o600)
open(kd + "/access_token", "w").write(KK)
os.chmod(kd + "/access_token", 0o600)

def mk(s):
    ls = s.split("\n")
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
            "source": [l + "\n" for l in ls[:-1]] + [ls[-1]]}

W0 = "print(\"RED-MIND CPU KEEPALIVE \u2014 GitHub Actions ne auto-restart kiya\")"
W_CF = "import os\nos.system(\"wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared && chmod +x cloudflared\")\nprint(\"cloudflared:\", os.path.exists(\"./cloudflared\"))\nassert os.path.exists(\"./cloudflared\"), \"cloudflared download fail!\""
C4 = "import subprocess, os, time\nos.environ[\"OLLAMA_URL_OVERRIDE\"] = \"http://localhost:11434\"\nif not os.path.exists(\"red-mind\"):\n    subprocess.run([\"git\",\"clone\",\"-q\",\"https://github.com/loverspubgking-afk/DARKZONE-MD.git\",\"red-mind\"], check=True)\nsubprocess.run([\"pip\",\"install\",\"-q\",\"httpx\",\"fastapi\",\"uvicorn\",\"beautifulsoup4\"], check=True)\nsubprocess.run([\"pip\",\"install\",\"-q\",\"playwright\"], check=False)\nsubprocess.run([\"python\",\"-m\",\"playwright\",\"install\",\"chromium\"], capture_output=True, timeout=900)\nsubprocess.run([\"python\",\"-m\",\"playwright\",\"install-deps\",\"chromium\"], capture_output=True, timeout=900)\napp_env = os.environ.copy()\nsubprocess.Popen([\"python\",\"-m\",\"uvicorn\",\"app:app\",\"--host\",\"0.0.0.0\",\"--port\",\"8000\"],\n                 cwd=\"red-mind\", env=app_env, stdout=open(\"app.log\",\"w\"), stderr=subprocess.STDOUT)\ntime.sleep(10)\nimport httpx\ntry:\n    print(\"RED-MIND APP:\", httpx.get(\"http://localhost:8000/api/health\", timeout=15).json())\nexcept Exception as e:\n    print(\"app error:\", e, open(\"red-mind/app.log\").read()[-300:])"
C_OMNI = "import subprocess, time, os, re, base64\nprint(\"Node 22 install (OmniRoute ko naya Node chahiye)...\")\nos.system(\"curl -fsSL https://deb.nodesource.com/setup_22.x | bash - > /dev/null 2>&1\")\nos.system(\"apt-get install -y nodejs > /dev/null 2>&1\")\nv = subprocess.run([\"node\",\"-v\"], capture_output=True, text=True).stdout.strip()\nprint(\"Node:\", v)\nprint(\"OmniRoute install...\")\nos.system(\"npm install -g omniroute 2>&1 | tail -1\")\nfor cmd in [[\"omniroute\",\"start\"], [\"omniroute\",\"serve\"], [\"omniroute\"]]:\n    try:\n        subprocess.Popen(cmd, stdout=open(\"omni.log\",\"w\"), stderr=subprocess.STDOUT)\n        time.sleep(15)\n        import httpx\n        r = httpx.get(\"http://localhost:20128/v1/models\", timeout=10)\n        if r.status_code == 200:\n            print(\"OMNIROUTE UP!\", cmd); break\n    except Exception:\n        continue\nelse:\n    print(\"omni log:\", open(\"omni.log\").read()[-200:] if os.path.exists(\"omni.log\") else \"no log\")\ntry:\n    import httpx\n    r = httpx.post(\"http://localhost:20128/v1/chat/completions\",\n        json={\"model\":\"auto\",\"messages\":[{\"role\":\"user\",\"content\":\"say OK\"}]}, timeout=60)\n    print(\"FREE TEST:\", r.status_code, r.text[:150])\nexcept Exception as e:\n    print(\"test err:\", e)\npo = subprocess.Popen([\"./cloudflared\",\"tunnel\",\"--url\",\"http://localhost:20128\"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)\nourl = None; t0 = time.time()\nwhile time.time() - t0 < 150:\n    line = po.stdout.readline()\n    if not line: time.sleep(0.5); continue\n    m = re.search(r\"https://[a-z0-9-]+\\.trycloudflare\\.com\", line)\n    if m: ourl = m.group(0); break\nprint(\"OMNI LINK:\", ourl)\ntry:\n    import httpx\n    hdr = {\"Authorization\": \"Bearer __GH_TOKEN__\"}\n    repo = \"https://api.github.com/repos/loverspubgking-afk/redmind-links/contents/omni-link.txt\"\n    r = httpx.get(repo, headers=hdr)\n    sha = r.json().get(\"sha\") if r.status_code == 200 else None\n    payload = {\"message\": \"omni\", \"content\": base64.b64encode((ourl or \"NA\").encode()).decode()}\n    if sha: payload[\"sha\"] = sha\n    print(\"upload:\", httpx.put(repo, headers=hdr, json=payload).status_code)\nexcept Exception as e:\n    print(\"GH fail:\", e)"
C5 = "import subprocess, re, time, base64\np2 = subprocess.Popen([\"./cloudflared\",\"tunnel\",\"--url\",\"http://localhost:8000\"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)\napp_url = None; t0 = time.time()\nwhile time.time() - t0 < 150:\n    line = p2.stdout.readline()\n    if not line: time.sleep(0.5); continue\n    m = re.search(r\"https://[a-z0-9-]+\\.trycloudflare\\.com\", line)\n    if m: app_url = m.group(0); break\nprint(\"LIVE LINK:\", app_url)\ntry:\n    import httpx\n    hdr = {\"Authorization\": \"Bearer __GH_TOKEN__\"}\n    repo = \"https://api.github.com/repos/loverspubgking-afk/redmind-links/contents/app-link.txt\"\n    r = httpx.get(repo, headers=hdr)\n    sha = r.json().get(\"sha\") if r.status_code == 200 else None\n    payload = {\"message\": \"app link\", \"content\": base64.b64encode((app_url or \"NA\").encode()).decode()}\n    if sha: payload[\"sha\"] = sha\n    print(\"upload:\", httpx.put(repo, headers=hdr, json=payload).status_code)\nexcept Exception as e:\n    print(\"GH fail:\", e)"
C6 = "import time, subprocess, os\ndef update_app():\n    subprocess.run([\"git\",\"fetch\",\"-q\",\"origin\"], cwd=\"red-mind\", capture_output=True)\n    l = subprocess.run([\"git\",\"rev-list\",\"HEAD..origin/main\",\"--count\"], cwd=\"red-mind\", capture_output=True, text=True)\n    if l.stdout.strip() not in (\"0\",\"\"):\n        subprocess.run([\"git\",\"pull\",\"-q\"], cwd=\"red-mind\", capture_output=True)\n        subprocess.run([\"pkill\",\"-f\",\"uvicorn app:app\"], capture_output=True)\n        time.sleep(2)\n        env = os.environ.copy()\n        subprocess.Popen([\"python\",\"-m\",\"uvicorn\",\"app:app\",\"--host\",\"0.0.0.0\",\"--port\",\"8000\"],\n                         cwd=\"red-mind\", env=env, stdout=open(\"app.log\",\"a\"), stderr=subprocess.STDOUT)\n        print(\"APP UPDATED\")\nfor i in range(48):\n    try: update_app()\n    except Exception as e: print(\"upd err:\", e)\n    time.sleep(600)\nprint(\"Session khatam\")"

c5 = C5.replace("__GH_TOKEN__", GH_TOKEN)
c_omni = C_OMNI.replace("__GH_TOKEN__", GH_TOKEN)

nb = {"cells": [mk(W0), mk(W_CF), mk(C4), mk(c_omni), mk(c5), mk(C6)],
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python", "version": "3.10"}},
      "nbformat": 4, "nbformat_minor": 4}

os.makedirs("/tmp/kpush", exist_ok=True)
json.dump(nb, open("/tmp/kpush/notebook.ipynb", "w"), indent=1)
json.dump({"id": "loverspubgking/red-mind-dolphin", "title": "red-mind-dolphin",
           "code_file": "notebook.ipynb", "language": "python", "kernel_type": "notebook",
           "is_private": "true", "enable_gpu": "false", "enable_internet": "true",
           "competition_sources": [], "dataset_sources": [], "kernel_sources": [], "model_sources": []},
          open("/tmp/kpush/kernel-metadata.json", "w"), indent=1)

r = subprocess.run(["kaggle", "kernels", "push", "-p", "/tmp/kpush"], capture_output=True, text=True)
print("STDOUT:", r.stdout.strip())
print("STDERR:", r.stderr.strip()[-300:] if r.stderr else "")
sys.exit(r.returncode)
