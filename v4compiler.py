#!/usr/bin/env python3
"""
v3compiler – Code Compiler GUI with Full Backend Integration
============================================================

A self‑contained graphical interface to archive a project’s source code into
one text file and later rebuild the exact folder structure from that archive.

Includes all functionality from the original code_compiler.py plus advanced
exclusion patterns (wildcards, .gitignore support).

Usage:
    python v3compiler.py

Made with 💖 by pavnxet
"""

import sys
import os
import threading
import queue
import argparse
import fnmatch
import tempfile
import stat
from pathlib import Path
from typing import Iterator, Tuple, Set, List, Optional

# Tkinter imports
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# ----------------------------------------------------------------------
# Backend – Collect & Reconstruct Logic (originally code_compiler.py)
# ----------------------------------------------------------------------

HEADER_SEP = "=" * 80

# Default extensions to include when collecting
DEFAULT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".htm", ".css", ".scss", ".sass",
    ".c", ".cpp", ".h", ".hpp", ".java", ".kt", ".kts", ".swift", ".go", ".rs",
    ".rb", ".php", ".pl", ".pm", ".sh", ".bash", ".zsh", ".fish",
    ".sql", ".r", ".m", ".mm", ".lua", ".vim",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg", ".conf",
    ".md", ".rst", ".tex", ".txt", ".csv",
    "Dockerfile", "Makefile", "CMakeLists.txt", "requirements.txt", "Gemfile",
    "package.json", "Cargo.toml", "go.mod", "go.sum",
}

# Directories to skip during collection (exact names or wildcard suffixes)
EXCLUDE_DIRS = {
    ".git", ".svn", ".hg", "__pycache__",
    "node_modules", "venv", ".venv", "env", ".env", "virtualenv",
    "dist", "build", "target", "out",
    ".idea", ".vscode", ".DS_Store",
    ".mypy_cache", ".pytest_cache", ".tox", ".eggs",
    "*.egg-info",
}

# ----------------------------------------------------------------------
# Security & Utility Functions (Backend)
# ----------------------------------------------------------------------
def same_file(path1: str, path2: str) -> bool:
    """Cross‑platform same‑file check."""
    try:
        return os.path.samefile(path1, path2)
    except AttributeError:
        return os.path.normcase(os.path.abspath(path1)) == os.path.normcase(os.path.abspath(path2))

def safe_path(output_root: str, rel_path: str) -> str:
    """Resolve a relative path within output_root; raise if escapes."""
    rel_path = rel_path.replace('\\', '/')
    root = Path(output_root).resolve()
    target = (root / rel_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError(f"Attempted directory traversal: {rel_path}")
    return str(target)

def atomic_write(filepath: str, content: bytes, mode: Optional[int] = None):
    """Write content atomically using a temporary file."""
    dirname = os.path.dirname(filepath)
    if mode is None:
        if os.path.exists(filepath):
            mode = stat.S_IMODE(os.stat(filepath).st_mode)
        else:
            mode = 0o644

    with tempfile.NamedTemporaryFile(dir=dirname, delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        temp_name = tmp.name

    os.chmod(temp_name, mode)
    os.replace(temp_name, filepath)

def is_text_file(filepath: str) -> bool:
    """Heuristic: read first 1KB; no null byte -> likely text."""
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            return b'\x00' not in chunk
    except Exception:
        return False

def read_file_content(filepath: str) -> str:
    """Read file with encoding fallbacks."""
    for enc in ('utf-8', 'utf-16', 'latin-1'):
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(filepath, 'rb') as f:
        return f.read().decode('utf-8', errors='replace')

def should_exclude_directory(dirname: str) -> bool:
    """Check if a directory name matches any exclusion pattern."""
    for pat in EXCLUDE_DIRS:
        if pat.startswith('*') and dirname.endswith(pat[1:]):
            return True
        if dirname == pat:
            return True
    return False

# ----------------------------------------------------------------------
# Collect Mode (Backend)
# ----------------------------------------------------------------------
def should_include_file(filepath: str, extensions: Set[str]) -> bool:
    _, ext = os.path.splitext(filepath)
    if ext.lower() in extensions:
        return True
    basename = os.path.basename(filepath)
    return basename in extensions

def collect_files(root_dir: str, script_path: str, output_path: str,
                  extensions: Set[str]) -> Iterator[Tuple[str, str]]:
    """Yield (rel_path, full_path) for files to include."""
    root_dir = os.path.abspath(root_dir)
    script_path = os.path.abspath(script_path)
    output_path = os.path.abspath(output_path)

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Prune excluded directories in-place (backend's own exclusions)
        dirnames[:] = [d for d in dirnames if not should_exclude_directory(d)]

        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, root_dir)
            rel_path = rel_path.replace('\\', '/')

            if same_file(full_path, script_path) or same_file(full_path, output_path):
                continue
            if any(should_exclude_directory(part) for part in rel_path.split('/')):
                continue
            if not should_include_file(full_path, extensions):
                continue
            if not is_text_file(full_path):
                print(f"Skipping binary: {rel_path}", file=sys.stderr)
                continue

            yield rel_path, full_path

def run_collect(args):
    script_path = os.path.abspath(__file__)
    root_dir = os.path.abspath(args.root)
    output_path = os.path.join(root_dir, args.output)

    extensions = set(args.extensions) if args.extensions else DEFAULT_EXTENSIONS.copy()
    if not args.no_default_extensions and args.extensions:
        extensions.update(DEFAULT_EXTENSIONS)

    print(f"Scanning root  : {root_dir}")
    print(f"Output file    : {output_path}")
    print(f"Extensions     : {len(extensions)} extensions")

    file_count = 0
    total_bytes = 0

    with open(output_path, 'w', encoding='utf-8') as outfile:
        for rel_path, full_path in collect_files(root_dir, script_path, output_path, extensions):
            file_count += 1
            print(f"  Adding: {rel_path}")

            outfile.write(f"\n\n{HEADER_SEP}\n")
            outfile.write(f"FILE: {rel_path}\n")
            outfile.write(f"{HEADER_SEP}\n\n")

            try:
                content = read_file_content(full_path)
                outfile.write(content)
                total_bytes += len(content.encode('utf-8'))
            except Exception as e:
                outfile.write(f"[ERROR reading file: {e}]\n")
                print(f"    Error: {e}", file=sys.stderr)

    print("\n" + "=" * 80)
    print(f"Done! Collected {file_count} files.")
    print(f"Output size: {total_bytes / 1024:.1f} KB")
    print(f"Output file: {output_path}")

# ----------------------------------------------------------------------
# Reconstruct Mode (Backend)
# ----------------------------------------------------------------------
def parse_dump_file(dump_path: str) -> Iterator[Tuple[str, str]]:
    """Yield (rel_path, content_str) using line‑by‑line state machine."""
    with open(dump_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        if len(lines) > 100000:
            print("Warning: Dump file is very large. Parsing may be slow.", file=sys.stderr)

    i = 0
    while i < len(lines):
        while i < len(lines) and lines[i].strip() == "":
            i += 1
        if i >= len(lines):
            break

        line = lines[i].rstrip('\n')
        if line.strip() != HEADER_SEP:
            i += 1
            continue

        i += 1
        if i >= len(lines):
            break
        file_line = lines[i].strip()
        if not file_line.startswith("FILE: "):
            i += 1
            continue
        rel_path = file_line[6:].strip()

        i += 1
        if i >= len(lines):
            break
        close_line = lines[i].rstrip('\n')
        if close_line.strip() != HEADER_SEP:
            i += 1
            continue

        i += 1
        content_lines = []
        while i < len(lines):
            if lines[i].rstrip('\n').strip() == HEADER_SEP:
                if i + 1 < len(lines) and lines[i+1].strip().startswith("FILE: "):
                    break
            content_lines.append(lines[i])
            i += 1

        content = "".join(content_lines).rstrip('\n')
        yield rel_path, content

def run_reconstruct(args):
    dump_path = args.dump_file
    if not os.path.isfile(dump_path):
        print(f"Error: Dump file not found: {dump_path}", file=sys.stderr)
        sys.exit(1)

    if args.output is None:
        dump_dir = os.path.dirname(os.path.abspath(dump_path))
        output_root = os.path.join(dump_dir, "restored")
    else:
        output_root = args.output

    if not args.dry_run:
        os.makedirs(output_root, exist_ok=True)

    # Pre‑scan for confirmation
    files_to_create: List[Tuple[str, str, bool]] = []
    for rel_path, _ in parse_dump_file(dump_path):
        try:
            target = safe_path(output_root, rel_path)
            exists = os.path.exists(target) if not args.dry_run else False
            files_to_create.append((rel_path, target, exists))
        except ValueError as e:
            print(f"Security error: {e}", file=sys.stderr)

    if args.confirm:
        print("Files to be created/overwritten:")
        for rel_path, _, exists in files_to_create:
            status = "OVERWRITE" if exists else "CREATE"
            print(f"  {status}: {rel_path}")
        response = input("\nProceed? [y/N] ").strip().lower()
        if response not in ('y', 'yes'):
            print("Aborted.")
            sys.exit(0)

    created = overwritten = skipped = errors = 0

    for rel_path, content in parse_dump_file(dump_path):
        try:
            target_path = safe_path(output_root, rel_path)
        except ValueError as e:
            print(f"Security error: {e}", file=sys.stderr)
            errors += 1
            continue

        file_exists = os.path.exists(target_path)
        if file_exists and not args.force:
            print(f"Skipping (already exists): {rel_path}")
            skipped += 1
            continue

        if args.dry_run:
            action = "Would overwrite" if file_exists else "Would create"
            print(f"{action}: {rel_path}")
            if file_exists:
                overwritten += 1
            else:
                created += 1
            continue

        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        try:
            file_bytes = content.encode('utf-8')
            atomic_write(target_path, file_bytes)

            action = "Overwrote" if file_exists else "Created"
            if file_exists:
                overwritten += 1
            else:
                created += 1
            print(f"{action}: {rel_path}")
        except Exception as e:
            print(f"Error writing {rel_path}: {e}", file=sys.stderr)
            errors += 1

    print("\n" + "=" * 80)
    if args.dry_run:
        print("DRY RUN – No files were actually written.")
    print(f"Reconstruction complete.")
    print(f"  Created    : {created}")
    print(f"  Overwritten: {overwritten}")
    print(f"  Skipped    : {skipped}")
    if errors:
        print(f"  Errors     : {errors}")
    if not args.dry_run:
        print(f"Output directory: {os.path.abspath(output_root)}")

# ----------------------------------------------------------------------
# GUI – Output Redirection & Main Application
# ----------------------------------------------------------------------

class QueueWriter:
    """File-like object that puts lines into a queue."""
    def __init__(self, queue, is_error=False):
        self.queue = queue
        self.is_error = is_error
        self.buffer = ""

    def write(self, text):
        if text:
            self.buffer += text
            if '\n' in self.buffer:
                lines = self.buffer.splitlines(True)
                self.buffer = ""
                for line in lines:
                    if line.endswith('\n'):
                        self.queue.put((line.rstrip('\n'), self.is_error))
                    else:
                        self.buffer = line

    def flush(self):
        if self.buffer:
            self.queue.put((self.buffer, self.is_error))
            self.buffer = ""

    def isatty(self):
        return False


class CodeCompilerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("v3compiler – Collect & Reconstruct")
        self.root.geometry("800x650")
        self.root.minsize(700, 550)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()

        self.output_queue = queue.Queue()
        self.running = False

        self._create_widgets()
        self._process_queue()

    def _configure_styles(self):
        self.style.configure("TNotebook", background="#f0f0f0")
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=6)
        self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
        self.style.configure("Status.TLabel", background="#e0e0e0", relief="sunken", padding=4)
        self.style.configure("Run.TButton", font=("Segoe UI", 11, "bold"), background="#4CAF50")

    def _create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        self.collect_tab = ttk.Frame(self.notebook)
        self.reconstruct_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.collect_tab, text="Collect")
        self.notebook.add(self.reconstruct_tab, text="Reconstruct")

        self._build_collect_tab()
        self._build_reconstruct_tab()

        log_frame = ttk.LabelFrame(self.root, text="Output Log", padding=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white"
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_config("stderr", foreground="#f48771")
        self.log_text.tag_config("stdout", foreground="#d4d4d4")
        self.log_text.tag_config("info", foreground="#6a9955")

        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, style="Status.TLabel")
        status_bar.pack(fill="x", padx=10, pady=(0, 10))

    def _build_collect_tab(self):
        frame = self.collect_tab
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Collect Source Files", style="Header.TLabel").grid(
            row=0, column=0, columnspan=3, pady=(15, 20), sticky="w", padx=20
        )

        ttk.Label(frame, text="Root Directory:").grid(row=1, column=0, sticky="w", padx=20, pady=5)
        self.collect_root_var = tk.StringVar(value=os.path.dirname(os.path.abspath(__file__)))
        ttk.Entry(frame, textvariable=self.collect_root_var, width=50).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(frame, text="Browse...", command=self._browse_collect_root).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(frame, text="Output File:").grid(row=2, column=0, sticky="w", padx=20, pady=5)
        self.collect_output_var = tk.StringVar(value="code_dump.txt")
        ttk.Entry(frame, textvariable=self.collect_output_var, width=50).grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(frame, text="Browse...", command=self._browse_collect_output).grid(row=2, column=2, padx=5, pady=5)

        ttk.Label(frame, text="Extensions:").grid(row=3, column=0, sticky="w", padx=20, pady=5)
        self.collect_ext_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.collect_ext_var, width=50).grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        ttk.Label(frame, text="e.g., .py .js .html", font=("Segoe UI", 8)).grid(row=3, column=2, padx=5, pady=5, sticky="w")

        ttk.Label(frame, text="Exclude patterns:").grid(row=4, column=0, sticky="w", padx=20, pady=5)
        self.collect_exclude_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.collect_exclude_var, width=50).grid(row=4, column=1, sticky="ew", padx=5, pady=5)
        ttk.Label(frame, text="Space-separated, e.g., node_modules *.log", font=("Segoe UI", 8)).grid(row=4, column=2, padx=5, pady=5, sticky="w")

        options_frame = ttk.Frame(frame)
        options_frame.grid(row=5, column=0, columnspan=3, pady=15, padx=20, sticky="w")

        self.use_default_ext_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Use default extensions", variable=self.use_default_ext_var).pack(anchor="w", pady=2)

        self.no_default_ext_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Use ONLY extensions provided above (ignore defaults)", variable=self.no_default_ext_var).pack(anchor="w", pady=2)

        self.use_gitignore_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Also exclude patterns from .gitignore (if present)", variable=self.use_gitignore_var).pack(anchor="w", pady=2)

        self.collect_run_btn = ttk.Button(frame, text="▶ Collect", style="Run.TButton", command=self._run_collect_threaded)
        self.collect_run_btn.grid(row=6, column=0, columnspan=3, pady=20)

    def _build_reconstruct_tab(self):
        frame = self.reconstruct_tab
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Reconstruct Project", style="Header.TLabel").grid(
            row=0, column=0, columnspan=3, pady=(15, 20), sticky="w", padx=20
        )

        ttk.Label(frame, text="Dump File:").grid(row=1, column=0, sticky="w", padx=20, pady=5)
        self.recon_dump_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.recon_dump_var, width=50).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(frame, text="Browse...", command=self._browse_recon_dump).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(frame, text="Output Directory:").grid(row=2, column=0, sticky="w", padx=20, pady=5)
        self.recon_output_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.recon_output_var, width=50).grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(frame, text="Browse...", command=self._browse_recon_output).grid(row=2, column=2, padx=5, pady=5)
        ttk.Label(frame, text="(leave blank for 'restored' next to dump)", font=("Segoe UI", 8)).grid(row=3, column=1, padx=5, pady=(0,10), sticky="w")

        options_frame = ttk.Frame(frame)
        options_frame.grid(row=4, column=0, columnspan=3, pady=5, padx=20, sticky="w")

        self.recon_force_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Force overwrite existing files", variable=self.recon_force_var).pack(anchor="w", pady=2)

        self.recon_dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Dry run (preview only, don't write files)", variable=self.recon_dry_run_var).pack(anchor="w", pady=2)

        self.recon_confirm_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Ask for confirmation before writing", variable=self.recon_confirm_var).pack(anchor="w", pady=2)

        self.recon_run_btn = ttk.Button(frame, text="▶ Reconstruct", style="Run.TButton", command=self._run_reconstruct_threaded)
        self.recon_run_btn.grid(row=5, column=0, columnspan=3, pady=20)

    # ------------------------------------------------------------------
    # Browse callbacks
    # ------------------------------------------------------------------
    def _browse_collect_root(self):
        path = filedialog.askdirectory(title="Select Root Directory")
        if path:
            self.collect_root_var.set(path)

    def _browse_collect_output(self):
        path = filedialog.asksaveasfilename(
            title="Save Output As",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.collect_output_var.set(path)

    def _browse_recon_dump(self):
        path = filedialog.askopenfilename(
            title="Select Dump File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.recon_dump_var.set(path)

    def _browse_recon_output(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.recon_output_var.set(path)

    # ------------------------------------------------------------------
    # Execution threading with exclusion monkey-patching
    # ------------------------------------------------------------------
    def _run_collect_threaded(self):
        if self.running:
            messagebox.showwarning("Busy", "An operation is already running.")
            return
        self._clear_log()
        self._set_running(True)
        threading.Thread(target=self._run_collect, daemon=True).start()

    def _run_reconstruct_threaded(self):
        if self.running:
            messagebox.showwarning("Busy", "An operation is already running.")
            return
        self._clear_log()
        self._set_running(True)
        threading.Thread(target=self._run_reconstruct, daemon=True).start()

    def _run_collect(self):
        try:
            args = argparse.Namespace()
            args.root = self.collect_root_var.get().strip()
            args.output = self.collect_output_var.get().strip()
            args.no_default_extensions = self.no_default_ext_var.get()

            ext_str = self.collect_ext_var.get().strip()
            args.extensions = ext_str.split() if ext_str else None

            # Build exclusion list from GUI patterns + .gitignore
            exclude_str = self.collect_exclude_var.get().strip()
            user_excludes = exclude_str.split() if exclude_str else []
            use_gitignore = self.use_gitignore_var.get()

            root_path = Path(args.root).resolve()
            all_excludes = set(user_excludes)

            if use_gitignore:
                gitignore_path = root_path / ".gitignore"
                if gitignore_path.is_file():
                    with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                all_excludes.add(line)
                                if "/" not in line and not line.startswith("*"):
                                    all_excludes.add(f"**/{line}/**")
                                    all_excludes.add(f"**/{line}")

            # Monkey-patch os functions to apply exclusions
            original_scandir = os.scandir
            original_walk = os.walk
            original_listdir = os.listdir

            def is_excluded(entry_path: Path) -> bool:
                try:
                    rel_path = str(entry_path.relative_to(root_path)).replace(os.sep, "/")
                except ValueError:
                    return False
                name = entry_path.name
                for pat in all_excludes:
                    if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(name, pat):
                        return True
                    if pat.endswith("/") and fnmatch.fnmatch(rel_path + "/", pat):
                        return True
                return False

            class FilteredScandirIterator:
                def __init__(self, original_iterator, root, excludes):
                    self._it = original_iterator
                    self._root = root
                    self._excludes = excludes

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    self._it.__exit__(exc_type, exc_val, exc_tb)

                def __iter__(self):
                    return self

                def __next__(self):
                    while True:
                        entry = next(self._it)
                        if not self._is_excluded(entry):
                            return entry

                def _is_excluded(self, entry):
                    try:
                        p = Path(entry.path)
                        rel_path = str(p.relative_to(self._root)).replace(os.sep, "/")
                        name = p.name
                        for pat in self._excludes:
                            if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(name, pat):
                                return True
                            if pat.endswith("/") and fnmatch.fnmatch(rel_path + "/", pat):
                                return True
                    except (OSError, ValueError):
                        pass
                    return False

            def filtered_scandir(path):
                it = original_scandir(path)
                return FilteredScandirIterator(it, root_path, all_excludes)

            def filtered_walk(top, topdown=True, onerror=None, followlinks=False):
                for root, dirs, files in original_walk(top, topdown, onerror, followlinks):
                    root_path_obj = Path(root)
                    dirs[:] = [d for d in dirs if not is_excluded(root_path_obj / d)]
                    files[:] = [f for f in files if not is_excluded(root_path_obj / f)]
                    yield root, dirs, files

            def filtered_listdir(path):
                entries = original_listdir(path)
                path_obj = Path(path)
                return [e for e in entries if not is_excluded(path_obj / e)]

            os.scandir = filtered_scandir
            os.walk = filtered_walk
            os.listdir = filtered_listdir

            # Redirect stdout/stderr
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = QueueWriter(self.output_queue, is_error=False)
            sys.stderr = QueueWriter(self.output_queue, is_error=True)

            try:
                run_collect(args)   # backend function
            except Exception as e:
                print(f"\nERROR: {e}", file=sys.stderr)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                os.scandir = original_scandir
                os.walk = original_walk
                os.listdir = original_listdir

        except Exception as e:
            self.output_queue.put((f"Fatal error: {e}", True))
        finally:
            self.root.after(0, self._set_running, False)

    def _run_reconstruct(self):
        try:
            args = argparse.Namespace()
            args.dump_file = self.recon_dump_var.get().strip()
            args.output = self.recon_output_var.get().strip() or None
            args.force = self.recon_force_var.get()
            args.dry_run = self.recon_dry_run_var.get()
            args.confirm = self.recon_confirm_var.get()

            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = QueueWriter(self.output_queue, is_error=False)
            sys.stderr = QueueWriter(self.output_queue, is_error=True)

            original_input = __builtins__.input
            try:
                if args.confirm:
                    def gui_input(prompt=""):
                        response_queue = queue.Queue()
                        self.root.after(0, lambda: response_queue.put(
                            messagebox.askyesno("Confirm", prompt) if args.confirm else "y"
                        ))
                        return response_queue.get()
                    __builtins__.input = gui_input
                else:
                    __builtins__.input = lambda _="": "y"

                run_reconstruct(args)   # backend function
            except Exception as e:
                print(f"\nERROR: {e}", file=sys.stderr)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                __builtins__.input = original_input

        except Exception as e:
            self.output_queue.put((f"Fatal error: {e}", True))
        finally:
            self.root.after(0, self._set_running, False)

    def _set_running(self, running):
        self.running = running
        if running:
            self.status_var.set("Running...")
            self.collect_run_btn.config(state="disabled")
            self.recon_run_btn.config(state="disabled")
        else:
            self.status_var.set("Ready")
            self.collect_run_btn.config(state="normal")
            self.recon_run_btn.config(state="normal")

    def _clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def _process_queue(self):
        try:
            while True:
                msg, is_error = self.output_queue.get_nowait()
                self.log_text.insert(tk.END, msg + "\n", "stderr" if is_error else "stdout")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self._process_queue)


# ----------------------------------------------------------------------
# Entry point (modified to accept initial directory argument)
# ----------------------------------------------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="v3compiler GUI")
    parser.add_argument("initial_dir", nargs="?", default=None,
                        help="Optional starting directory for the Root field")
    args = parser.parse_args()

    root = tk.Tk()
    app = CodeCompilerGUI(root)

    # If a directory was passed, set it as the initial Root Directory
    if args.initial_dir and os.path.isdir(args.initial_dir):
        app.collect_root_var.set(os.path.abspath(args.initial_dir))

    root.mainloop()


if __name__ == "__main__":
    main()