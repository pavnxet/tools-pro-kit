# 🛠️ Auto-Updating README Tree Guide

This guide explains how to set up a GitHub Action to automatically update a directory tree inside your `README.md` whenever you push changes to the repository.

### 1. Prepare your README.md
Add these specific comment markers to your `README.md` where you want the tree to appear. The script uses these to identify the target area.

```markdown
## 📁 Project Structure
```

---

### 2. Create the Workflow File
Create a new file in your repo at `.github/workflows/update-readme-tree.yml` and paste the following configuration:

```yaml
name: Update README Tree

on:
  push:
    branches: [ main ]
  workflow_dispatch: # Allows manual trigger

jobs:
  update-tree:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Generate and update tree
        uses: RavelloH/readme-tree@latest

      - name: Commit and push changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add README.md
          git commit -m "docs: update repository tree [skip ci]" || exit 0
          git push
```

---

### 3. Key Notes for Usage
* **Permissions:** Ensure your repository settings allow GitHub Actions to write to the repository (found under **Settings > Actions > General > Workflow permissions**).
* **Exclusions:** By default, common folders like `.git` are excluded.
* **Trigger:** The tree updates automatically on every push to the `main` branch.

---
