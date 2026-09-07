#!/usr/bin/env python3
"""
Batch-create one GitHub repo per student from the ML & FinTech roster and add
each student as a collaborator.

======================  HOW TO USE  ======================
1. Set your token as an environment variable (NEVER paste it into a chat):
       export GITHUB_TOKEN=xxxxxxxxxxxxxxxx
   - Classic PAT: needs the `repo` scope. To create repos in an ORG, the token
     owner must be allowed to create repos in that org (org member/owner).
   - Fine-grained PAT: grant the org (or your account) "Administration:
     read & write" and "Contents: read & write".

2. Edit the CONFIG block below (OWNER, OWNER_TYPE, naming, visibility...).

3. Dry run first — with DRY_RUN = True nothing is changed; it only prints the
   plan and validates every username against the GitHub API:
       python create_repos.py

4. When the plan looks right, set DRY_RUN = False and run again to actually
   create the repos and send the collaborator invites.

Requires: Python 3.8+ and `requests`  ->  pip install requests
==========================================================
"""

import csv
import os
import re
import sys
import time

import requests

# ----------------------------  CONFIG  ----------------------------
CSV_PATH          = "mlfintech_roster.csv"

OWNER             = "HWTeng-Teaching"  # org name, OR your own GitHub username
OWNER_TYPE        = "org"                   # "org"  or  "user"

# Repo name = f"{REPO_PREFIX}{SEP}{key}" where key comes from KEY_FIELD.
REPO_PREFIX       = "202609-ML-FinTech"
SEP               = "-"
KEY_FIELD         = "github"                # "github" (recommended, unique) or "student_id"

VISIBILITY        = "private"              # "private" or "public"
INIT_README       = True                   # create an initial commit with a README

ADD_COLLABORATOR  = True                    # invite the student to their repo
COLLAB_PERMISSION = "push"                  # pull / triage / push / maintain / admin

DRY_RUN           = True                    # keep True until you've reviewed the plan
RESULTS_CSV       = "repo_results.csv"
SLEEP_BETWEEN     = 0.5                     # seconds between API calls (be gentle)
# ------------------------------------------------------------------

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN")


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


if not TOKEN:
    fail("GITHUB_TOKEN environment variable is not set.")

if OWNER == "YOUR-ORG-OR-USERNAME":
    fail("Please edit the CONFIG block and set OWNER (and the other options).")

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
})


def sanitize_repo_name(raw: str) -> str:
    """GitHub allows letters, digits, '.', '_', '-'. Replace anything else."""
    name = re.sub(r"[^A-Za-z0-9._-]", "-", raw.strip())
    return re.sub(r"-{2,}", "-", name).strip("-")


def check_rate_limit(resp):
    if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
        reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
        wait = max(reset - int(time.time()), 1)
        print(f"  ! Rate limited. Sleeping {wait}s ...")
        time.sleep(wait + 1)
        return True
    return False


def user_exists(username: str) -> bool:
    r = session.get(f"{API}/users/{username}")
    return r.status_code == 200


def repo_exists(owner: str, repo: str) -> bool:
    r = session.get(f"{API}/repos/{owner}/{repo}")
    return r.status_code == 200


def create_repo(repo: str) -> tuple[bool, str]:
    payload = {
        "name": repo,
        "private": VISIBILITY == "private",
        "auto_init": INIT_README,
        "description": f"{REPO_PREFIX} personal repo",
    }
    if OWNER_TYPE == "org":
        url = f"{API}/orgs/{OWNER}/repos"
    else:
        # Only creates in the *authenticated* user's account; OWNER must be you.
        url = f"{API}/user/repos"
    r = session.post(url, json=payload)
    if check_rate_limit(r):
        r = session.post(url, json=payload)
    if r.status_code == 201:
        return True, "created"
    return False, f"create failed [{r.status_code}] {r.json().get('message', '')}"


def add_collaborator(repo: str, username: str) -> tuple[bool, str]:
    url = f"{API}/repos/{OWNER}/{repo}/collaborators/{username}"
    r = session.put(url, json={"permission": COLLAB_PERMISSION})
    if check_rate_limit(r):
        r = session.put(url, json={"permission": COLLAB_PERMISSION})
    if r.status_code == 201:
        return True, "invite sent"
    if r.status_code == 204:
        return True, "already a collaborator"
    return False, f"invite failed [{r.status_code}] {r.json().get('message', '')}"


def main():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("github", "").strip()]

    print(f"Loaded {len(rows)} students with a GitHub account.")
    print(f"Mode: {'DRY RUN (no changes)' if DRY_RUN else '*** LIVE — will create repos & send invites ***'}")
    print(f"Owner: {OWNER} ({OWNER_TYPE}) | visibility: {VISIBILITY} | "
          f"collaborator: {ADD_COLLABORATOR} ({COLLAB_PERMISSION})\n")

    results = []
    for i, row in enumerate(rows, 1):
        gh = row["github"].strip()
        key = row.get(KEY_FIELD, gh).strip() or gh
        repo = sanitize_repo_name(f"{REPO_PREFIX}{SEP}{key}")
        label = f"{row.get('name','') or row.get('nickname','')} ({gh})"
        status = {"name": row.get("name", ""), "nickname": row.get("nickname", ""),
                  "github": gh, "repo": repo, "user_ok": "", "repo": repo,
                  "repo_action": "", "collab_action": ""}

        print(f"[{i}/{len(rows)}] {label} -> {OWNER}/{repo}")

        # 1) validate the username actually exists (catches typos in the sheet)
        exists = True
        if not DRY_RUN or True:  # always validate, even in dry run
            exists = user_exists(gh)
            time.sleep(SLEEP_BETWEEN)
        status["user_ok"] = "yes" if exists else "NO — username not found"
        if not exists:
            print("  ! GitHub user not found. Skipping (check the spreadsheet).")
            results.append(status)
            continue

        # 2) create repo (idempotent: skip if it already exists)
        if repo_exists(OWNER, repo):
            status["repo_action"] = "already exists (skipped)"
            print("  = repo already exists, skipping create.")
        elif DRY_RUN:
            status["repo_action"] = "would create"
            print("  ~ would create repo.")
        else:
            ok, msg = create_repo(repo)
            status["repo_action"] = msg
            print(f"  {'+' if ok else '!'} {msg}")
            time.sleep(SLEEP_BETWEEN)

        # 3) add collaborator
        if ADD_COLLABORATOR:
            if DRY_RUN:
                status["collab_action"] = "would invite"
                print(f"  ~ would invite {gh} as {COLLAB_PERMISSION}.")
            elif status["repo_action"].startswith(("create failed",)):
                status["collab_action"] = "skipped (repo failed)"
            else:
                ok, msg = add_collaborator(repo, gh)
                status["collab_action"] = msg
                print(f"  {'+' if ok else '!'} {msg}")
                time.sleep(SLEEP_BETWEEN)

        results.append(status)

    # write a results log
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "nickname", "github", "repo",
                                          "user_ok", "repo_action", "collab_action"])
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k, "") for k in w.fieldnames})

    bad = [r for r in results if r["user_ok"].startswith("NO")]
    print(f"\nDone. Log written to {RESULTS_CSV}.")
    if bad:
        print(f"{len(bad)} username(s) not found on GitHub — verify these in the sheet:")
        for r in bad:
            print(f"  - {r.get('name') or r.get('nickname')}: {r['github']}")


if __name__ == "__main__":
    main()
