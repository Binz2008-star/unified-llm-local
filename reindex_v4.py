"""
Second Brain v4 - Phase 2: AST chunking + hybrid re-index
- Runs ASTChunker on all indexable files (function/class level for Python)
- Embeds via Ollama (nomic-embed-text, 768-dim) in batches with retry
- REPLACES old 'generic' rows per file (delete + insert) to avoid duplication
- Builds code_graph edges from Python imports
- Per-file resume via logs/reindex_state.json

Usage:
  python reindex_v4.py --scan             # count files + estimated chunks, no writes
  python reindex_v4.py --project lvyy     # index one project
  python reindex_v4.py --project rico --all   # force redo even if marked done
  python reindex_v4.py                    # index all remaining
"""
import asyncio
import hashlib
import json
import os
import sys
import ast
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
import asyncpg
import aiohttp

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "v4-extract" / "second-brain-v4"))
from chunker_v4 import ASTChunker  # noqa: E402

load_dotenv(ROOT / ".env")

NEON_DSN = os.getenv("NEON_DSN", "")
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embed")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

PROJECT_ROOTS = {
    "content-engine": Path(os.getenv("PROJECT_CONTENT_ENGINE", "")),
    "lvyy": Path(os.getenv("PROJECT_LVYY", "")),
    "rico": Path(os.getenv("PROJECT_RICO", "")),
}

# Project-specific dirs to ignore (e.g. rico's large tests/ tree adds low-value noise)
PROJECT_EXTRA_IGNORE = {
    "rico": {"tests"},
}

BATCH = 16
LOG_DIR = ROOT / "logs"
STATE_FILE = LOG_DIR / "reindex_state.json"

IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "env", "dist", "build",
               ".next", ".turbo", "target", "bin", "obj", ".idea", ".vscode", ".vs", "coverage",
               ".pytest_cache", ".mypy_cache", ".ruff_cache", "site-packages", ".gradle", ".maven",
               "vendor", "Pods", ".expo", ".vercel", ".netlify", "tmp_frames", "tmp_inspect", "assets",
               # rico repo noise
               "data", "learning_cache", "worktrees", ".worktrees", ".playwright-mcp", ".devin",
               ".tours", ".local-ops", "AI_WORKSPACE", "design-handoffs", "learning",
               "rico-reply-hardening", "architecture_docs", "test-output", ".agents", ".claude",
               ".github", ".tours", ".agents", "migrations_archive", "htmlcov", ".ruff_cache",
               # generated build/static artifacts (OpenNext/Wrangler)
               ".open-next", ".wrangler", "public"}
IGNORE_EXTS = {".exe", ".dll", ".so", ".dylib", ".bin", ".zip", ".tar", ".gz", ".7z", ".rar",
               ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".mp4", ".mp3", ".avi", ".mov",
               ".pdf", ".pyc", ".pyo", ".o", ".a", ".svg", ".woff", ".woff2", ".ttf", ".lock", ".map"}
IGNORE_FILES = {".DS_Store", "Thumbs.db", "desktop.ini", ".env"}
MAX_FILE_SIZE = 5 * 1024 * 1024


def get_language(file_path: str):
    ext = Path(file_path).suffix.lower()
    name = Path(file_path).name.lower()
    lang_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "tsx", ".jsx": "jsx",
        ".md": "markdown", ".mdx": "mdx", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".toml": "toml", ".sql": "sql", ".sh": "bash", ".ps1": "powershell",
        ".html": "html", ".css": "css", ".scss": "scss", ".vue": "vue", ".svelte": "svelte",
        ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin", ".cpp": "cpp", ".c": "c",
        ".h": "c", ".hpp": "cpp", ".cs": "csharp", ".php": "php", ".rb": "ruby", ".swift": "swift",
        ".dart": "dart", ".lua": "lua", ".rst": "rst", ".txt": "text", ".ini": "ini", ".cfg": "cfg",
        ".conf": "conf", ".lock": "json", ".map": "json",
    }
    if name in ("dockerfile", "makefile", "rakefile", "gemfile", "procfile"):
        return name
    return lang_map.get(ext, "text")


def should_index(file_path: Path, root: Path, extra_ignore=frozenset()):
    try:
        rel_parts = file_path.relative_to(root).parts
        if any(p in IGNORE_DIRS or p in extra_ignore for p in rel_parts):
            return False
    except ValueError:
        return False
    if file_path.name in IGNORE_FILES:
        return False
    # Machine-generated size/noise files
    if file_path.name.lower() in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
                                   "composer.lock", "pip.lock", "npm-shrinkwrap.json", "bun.lock",
                                   "uv.lock", "cargo.lock", "flake.lock"):
        return False
    # Never index secrets/tokens
    lname = file_path.name.lower()
    if lname in ("token.json", "client_secret.json", ".env") or lname.startswith("client_secret") \
            or "credential" in lname or lname.endswith(".pem") or lname.endswith(".key"):
        return False
    if file_path.suffix.lower() in IGNORE_EXTS:
        return False
    if file_path.name.startswith(".") and file_path.name not in (".gitignore", ".aiderignore", ".env.example"):
        if file_path.suffix.lower() not in {".py", ".js", ".ts", ".json", ".md"}:
            return False
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE or file_path.stat().st_size < 10:
            return False
    except OSError:
        return False
    allowed = {".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt", ".json", ".yaml", ".yml", ".toml",
               ".ini", ".cfg", ".conf", ".sql", ".sh", ".ps1", ".html", ".css", ".scss", ".vue",
               ".svelte", ".go", ".rs", ".java", ".kt", ".cpp", ".c", ".h", ".hpp", ".cs", ".php",
               ".rb", ".swift", ".dart", ".lua", ".mdx", ".rst"}
    if file_path.suffix.lower() in allowed:
        return True
    if file_path.name.lower() in {"dockerfile", "makefile", ".gitignore", ".aiderignore",
                                  ".env.example", "requirements.txt", "package.json", "cargo.toml", "go.mod"}:
        return True
    return False


def sha256_hash(content: str):
    return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()


# ---- Python import resolution for code_graph ----
def extract_imports(text: str):
    """Return list of module-level import specs: (abs_path, [names]) and (rel, module, names)"""
    imports = []
    try:
        tree = ast.parse(text)
    except Exception:
        return imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imports.append(("import", a.name))
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            imports.append(("from", node.module or "", [a.name for a in node.names]))
        elif isinstance(node, ast.ImportFrom) and node.level > 0:
            imports.append(("rel", node.level, node.module or "", [a.name for a in node.names]))
    return imports


def module_to_paths(module: str):
    """a.b.c -> candidate relative file paths"""
    parts = module.split(".")
    base = "/".join(parts)
    return [base + ".py", base + "/__init__.py"]


def resolve_edges(project_root: Path, rel_file: str, text: str):
    """Resolve python imports to local file paths -> list of (source_rel, target_rel)"""
    edges = []
    imps = extract_imports(text)
    if not imps:
        return edges
    src_dir = Path(rel_file).parent.as_posix()
    roots = [project_root]
    src_root = project_root / "src"
    if src_root.exists():
        roots.insert(0, src_root)

    is_pkg = {p.as_posix() for p in (project_root / "src").rglob("*")} if src_root.exists() else set()

    def find_target(module):
        for m in module_to_paths(module):
            for r in roots:
                cand = r / m
                if cand.is_file():
                    return cand.relative_to(project_root).as_posix()
        return None

    for kind, *rest in imps:
        if kind == "import":
            module = rest[0]
            # top-level package name may be the whole module or first part
            tgt = find_target(module)
            if tgt:
                edges.append(tgt)
            else:
                first = module.split(".")[0]
                tgt = find_target(first)
                if tgt:
                    edges.append(tgt)
        elif kind == "from":
            module = rest[0]
            tgt = find_target(module)
            if tgt:
                edges.append(tgt)
        elif kind == "rel":
            level, module, _ = rest
            if level == 1:
                tgt = ".".join([src_dir.replace("/", "."), module]) if module else src_dir
            else:
                up = src_dir.split("/")[:- (level - 1)] if level - 1 else []
                base = ".".join(up + ([module] if module else []))
                tgt = base
            if tgt:
                hit = find_target(tgt)
                if hit:
                    edges.append(hit)
    return edges


# ---- Embedding ----
async def embed_batch(session, texts, retries=4):
    # Filter out empty texts, replace with zero vectors
    filtered = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
    if not filtered:
        return [[0.0] * 768] * len(texts)
    
    filtered_texts = [t for _, t in filtered]
    filtered_indices = [i for i, _ in filtered]
    
    for attempt in range(retries):
        try:
            async with session.post(OLLAMA_EMBED_URL,
                                    json={"model": EMBED_MODEL, "input": filtered_texts},
                                    timeout=aiohttp.ClientTimeout(total=180)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "embeddings" in data:
                        # Reconstruct full embeddings list with zero vectors for empty texts
                        embeddings = []
                        fi = 0
                        for i in range(len(texts)):
                            if i in filtered_indices:
                                embeddings.append(data["embeddings"][fi])
                                fi += 1
                            else:
                                embeddings.append([0.0] * 768)
                        return embeddings
                else:
                    body = (await resp.text())[:200]
                    if attempt == retries - 1:
                        raise RuntimeError(f"embed http {resp.status}: {body}")
            await asyncio.sleep(1)
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(2 * (attempt + 1))
    return None


# ---- DB ----
async def db_connect():
    return await asyncpg.connect(NEON_DSN, timeout=60, command_timeout=300)


async def write_file(conn, project_id, rel_path, chunks):
    """DELETE old rows for file + bulk INSERT new AST chunks. Returns row count."""
    async with conn.transaction():
        await conn.execute(
            "DELETE FROM chunks_v4 WHERE project_id=$1 AND file_path=$2", project_id, rel_path)
        await conn.executemany("""
            INSERT INTO chunks_v4 (project_id, file_path, chunk_index, chunk_type, chunk_name,
                                   content, content_hash, language, start_line, end_line,
                                   embedding, imports, calls)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::vector,$12,$13)
        """, chunks)
    return len(chunks)


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state):
    LOG_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---- Main pipeline ----
def chunk_file(content: str, rel_path: str):
    """Run ASTChunker and build insert-ready tuples."""
    lang = get_language(rel_path)
    cchunks = ASTChunker().chunk(content, rel_path)
    rows = []
    for i, cc in enumerate(cchunks):
        # Skip oversized chunks (>500k chars) that would overflow tsvector (max ~1MB)
        if len(cc.content) > 500_000:
            continue
        type_ = cc.type
        name = cc.name
        rows.append({
            "path": rel_path,
            "idx": i,
            "type": type_,
            "name": name,
            "content": cc.content,
            "hash": sha256_hash(cc.content),
            "lang": lang,
            "s": cc.start_line,
            "e": cc.end_line,
            "emb": None,
            "imports": None,
            "calls": None,
        })
    return rows


def collect_files(project_id):
    root = PROJECT_ROOTS[project_id]
    extra = PROJECT_EXTRA_IGNORE.get(project_id, ())
    files = [
        f
        for f in walk_pruned(root)
        if f.is_file() and should_index(f, root, extra)
    ]
    return root, files


def walk_pruned(root: Path):
    """os.walk with IGNORE_DIRS pruning (fast on huge trees)"""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            yield Path(dirpath) / fn


async def index_project(pool, session, project_id, force=False):
    root = PROJECT_ROOTS[project_id]
    if not root.exists():
        print(f"SKIP {project_id}: path {root} missing")
        return 0, 0, 0
    root, files = collect_files(project_id)
    state = load_state()
    done = set(state.get(project_id, {}).get("done", []))
    todo = [f for f in files if force or f.relative_to(root).as_posix() not in done]
    todo.sort(key=lambda f: f.as_posix())
    print(f"\nPROJECT {project_id} @ {root}: {len(files)} files, {len(todo)} todo")
    if not todo:
        return 0, 0, 0

    done_count = len(done)
    chunks_total = 0
    fail_count = 0
    for pos, f in enumerate(todo, 1):
        rel = f.relative_to(root).as_posix()
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            if len(content.strip()) < 20:
                done.add(rel); continue
            rows = chunk_file(content, rel)
            if not rows:
                done.add(rel); continue
            texts = [r["content"] for r in rows]
            embs = []
            for i in range(0, len(texts), BATCH):
                embs.extend(await embed_batch(session, texts[i:i + BATCH]))
            if len(embs) != len(rows) or any(e is None for e in embs):
                print(f"  FAIL embed {rel} ({len(embs)}/{len(rows)} embeds) - skipping")
                fail_count += 1
                continue
            for r, e in zip(rows, embs):
                r["emb"] = e
            db_rows = [(project_id, rel, r["idx"], r["type"], r["name"], r["content"],
                        r["hash"], r["lang"], r["s"], r["e"],
                        "[" + ",".join(f"{x:.6f}" for x in r["emb"]) + "]",
                        r["imports"], r["calls"]) for r in rows]
            async with pool.acquire() as conn:
                n = await write_file(conn, project_id, rel, db_rows)
            chunks_total += n
            done.add(rel)
            print(f"  [{pos}/{len(todo)}] {rel}: {n} chunks")
            if pos % 50 == 0:
                state.setdefault(project_id, {})["done"] = sorted(done)
                state[project_id]["chunks_total"] = chunks_total
                save_state(state)
        except Exception as e:
            print(f"  ERR {rel}: {e}")
            fail_count += 1

    state.setdefault(project_id, {})["done"] = sorted(done)
    state[project_id]["chunks_total"] = chunks_total
    state[project_id]["last_run"] = datetime.now().isoformat()
    save_state(state)
    print(f"\nPROJECT {project_id} DONE: +{chunks_total} chunks (+{len(done) - done_count} files), {fail_count} fails")
    return len(done), chunks_total, fail_count


async def build_graph(pool, project_id, force=False):
    """Build code_graph import edges for python files in project."""
    root = PROJECT_ROOTS[project_id]
    if not root.exists():
        return 0
    if not force and load_state().get(project_id, {}).get("graph_done"):
        print(f"GRAPH {project_id}: already built (use --all to rebuild)")
        return 0
    print(f"BUILDING code_graph for {project_id} ...")
    extra = PROJECT_EXTRA_IGNORE.get(project_id, ())
    edges = []
    for f in root.rglob("*.py"):
        if not f.is_file() or not should_index(f, root, extra):
            continue
        rel = f.relative_to(root).as_posix()
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for tgt in resolve_edges(root, rel, text):
            edges.append((project_id, rel, tgt, "imports"))
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM code_graph WHERE project_id=$1", project_id)
            await conn.executemany("""
                INSERT INTO code_graph (project_id, source_file, target_file, relation)
                VALUES ($1,$2,$3,$4)
            """, edges)
    st = load_state()
    st.setdefault(project_id, {})["graph_done"] = True
    save_state(st)
    print(f"GRAPH {project_id}: {len(edges)} import edges")
    return len(edges)


async def make_session():
    return aiohttp.ClientSession()


async def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--project", type=str, default=None)
    ap.add_argument("--all", action="store_true", help="force redo incl. graph rebuild")
    ap.add_argument("--no-graph", action="store_true")
    args = ap.parse_args()

    if args.scan:
        for pid, root in PROJECT_ROOTS.items():
            if not root.exists():
                print(f"{pid}: MISSING {root}")
                continue
            fs = collect_files(pid)[1]
            py = sum(1 for f in fs if f.suffix == ".py")
            est = 0
            for f in fs:
                try:
                    if f.suffix == ".py":
                        t = f.read_text(encoding="utf-8", errors="ignore")
                        est += max(1, len(t) // 1500)
                    else:
                        est += 1
                except Exception:
                    est += 1
            print(f"{pid}: {len(fs)} files ({py} python, ~{est} est. chunks)")
        return

    pool = await asyncpg.create_pool(NEON_DSN, min_size=2, max_size=8, command_timeout=300)
    session = await make_session()
    try:
        # Ensure all configured projects exist (satisfies chunks_v4 FK)
        async with pool.acquire() as conn:
            for pid, pj in PROJECT_ROOTS.items():
                await conn.execute("""INSERT INTO projects (id, name, path)
                    VALUES ($1,$2,$3) ON CONFLICT (id) DO UPDATE SET path=EXCLUDED.path""",
                    pid, pid, pj.as_posix())
        for pid in PROJECT_ROOTS:
            if args.project and pid != args.project:
                continue
            await index_project(pool, session, pid, force=args.all)
            if not args.no_graph:
                await build_graph(pool, pid, force=args.all)
    finally:
        await session.close()
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())