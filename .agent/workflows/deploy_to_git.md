---
description: Commits and pushes changes to the git repository.
---

1. ACQUIRE GIT PATH:
   Use `C:\Program Files\Git\bin\git.exe` as the executable path since it is not in the system PATH.

2. ADD CHANGES:
   Run command: `& "C:\Program Files\Git\bin\git.exe" add .`

3. COMMIT CHANGES:
   Run command: `& "C:\Program Files\Git\bin\git.exe" commit -m "Update: {Commit Message}"`
   *Note: Replace {Commit Message} with a concise summary of the changes.*

4. PUSH CHANGES:
   Run command: `& "C:\Program Files\Git\bin\git.exe" push`

5. VERIFY:
   Check the output of the push command to ensure success.
