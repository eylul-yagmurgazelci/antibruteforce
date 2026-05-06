#!/usr/bin/env python3
import subprocess
import os

os.chdir(r"c:\Users\acern\OneDrive\Desktop\siber")

# Get all commits
result = subprocess.run(
    ["git", "log", "--all", "--pretty=format:%H"],
    capture_output=True,
    text=True
)

commits = result.stdout.strip().split('\n')

# Reset to root
subprocess.run(["git", "reset", "--hard", "HEAD"], check=True)

# Rebase from root
root_commit = commits[-1]

# Create rebase script
rebase_script = ""
for commit in commits:
    rebase_script += f"pick {commit}\n"

# Execute git rebase with script
env = os.environ.copy()
env["GIT_SEQUENCE_EDITOR"] = "cat"
env["FILTER_BRANCH_SQUELCH_WARNING"] = "1"

# Alternative: use git filter-branch with mailmap
mailmap_content = "Eyul Yagmur Gazelci <eylulgazelci09@gmail.com> Abdul <>\n"

with open(".mailmap", "w") as f:
    f.write(mailmap_content)

print("Mailmap dosyasi olusturuldu")
print("Simdi: git log --all --pretty=format:%an ile kontrol edin")
