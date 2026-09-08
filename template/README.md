# Student Repo Setup

Automated setup that turns a class roster into one private GitHub repo per student, with the student added as a collaborator. Runs entirely from the command line — no manual repo creation.

## How it works

1. Students fill in a Google Form (name, student ID, course, GitHub username, email).
2. Responses land in a Google Sheet. Export it as CSV → `mlfintech_roster.csv`.
3. Run `create_repos.py`. For every row with a GitHub username, it:
   - creates `202609-ML-FinTech/<student_id>-<nickname>` (private repo), skipping any that already exist,
   - adds the student as a collaborator (`push` access),
   - logs the result of every row to `repo_results.csv`.

## Files

| File | Purpose |
|---|---|
| `mlfintech_roster.csv` | Roster exported from the Google Sheet. Columns: `name, student_id, course, nickname, github`. |
| `create_repos.py` | The setup script. Config is at the top of the file. |
| `repo_results.csv` | Written after each run — one row per student: created / skipped / failed. |

## Prerequisites

- Install Python 3.8+ and the `requests` library in the terminal: `pip install requests`
- A **GitHub classic Personal Access Token** with the **`repo`** scope only (Fine-grained tokens need extra org-level setup — classic is simpler for this).
  Create one at `github.com/settings/tokens` → **Generate new token (classic)**.
  <img width="1101" height="339" alt="截圖 2026-09-08 下午1 51 39" src="https://github.com/user-attachments/assets/699a69bb-8085-4ba2-8be0-bb722c398815" />
  <img width="1169" height="615" alt="截圖 2026-09-08 下午1 53 18" src="https://github.com/user-attachments/assets/bf7d58ab-2023-4747-ab76-7c2aba6dc448" />
  Choose repo scope; the others remain default. → Generate token



- The GitHub account behind that token must be an **Owner** (or have repo-creation rights) on the `202609-ML-FinTech` organization.
  Check at `github.com/orgs/Organiztion-name/people`.

## Running it

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxx      # never commit or paste this anywhere
python3 create_repos.py                       # dry run first (default: DRY_RUN = True)
```

Review the printed plan — it validates every GitHub username and flags any that don't exist. When it looks right, open `create_repos.py`, set `DRY_RUN = False`, and run it again to actually create the repos and send the invites.

Re-running later (new students, dropped course) is safe: existing repos are left alone, only permissions are refreshed.

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `403 You need admin access to the organization...` | The token's account isn't an Owner of the org (or isn't a member at all). | Check `github.com/orgs/202609-ML-FinTech/people` — confirm the account is listed with role **Owner**. |
| Same 403 even after becoming Owner | Using a **fine-grained** token whose Resource owner is your personal account, not the org — it can't create org repos regardless of permissions checked. | Switch to a **classic** token (`repo` scope only) — it always follows your account's current permissions, no extra org setup needed. |
| `404 Not Found` on `/orgs/<org>/memberships/<user>` | The token's account isn't a member of the org at all — wrong org name, or the role change was made on a different account. | Confirm the exact org URL in a browser, and confirm which GitHub login the token belongs to (`curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user`). |
| A student's row is skipped with "GitHub user not found" | Typo in the GitHub username column. | Fix in the Google Sheet, re-export the CSV, re-run — already-created repos are untouched. |

## Notes

- Repo names use `student_id-nickname` (e.g. `113700058-Ella`), not the student's real name, to keep names URL-safe and unique.
- Repos are created **private** by default; the professor (org member) and TAs can be given access via an org team with `maintain` permission, separate from this script.
