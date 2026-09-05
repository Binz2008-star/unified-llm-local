import re
import ast
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

try:
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

@dataclass
class CodeChunk:
    content: str
    type: str  # 'function', 'class', 'import', 'doc', 'generic'
    name: Optional[str]
    start_line: int
    end_line: int
    language: str

class ASTChunker:
    """
    SOTA chunker - understands code structure, not just char count
    Splits by functions, classes, with overlap and context
    """
    
    def __init__(self, max_chars=1500, overlap=200):
        self.max_chars = max_chars
        self.overlap = overlap
    
    def chunk_python(self, text: str) -> List[CodeChunk]:
        """AST-aware Python chunking"""
        try:
            tree = ast.parse(text)
        except:
            # Fallback to generic chunker
            return self.chunk_generic(text, "python")
        
        chunks = []
        lines = text.splitlines()
        
        # Extract imports as one chunk
        imports = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(node)
        
        if imports:
            start = imports[0].lineno
            end = imports[-1].end_lineno if hasattr(imports[-1], 'end_lineno') else imports[-1].lineno
            content = "\n".join(lines[start-1:end])
            chunks.append(CodeChunk(content, "import", None, start, end, "python"))
        
        # Extract classes and functions with full bodies
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                start = node.lineno
                end = getattr(node, 'end_lineno', start + 20)
                content = "\n".join(lines[start-1:end])
                # If class too big, split methods
                if len(content) > self.max_chars * 1.5:
                    # Keep class header + each method as separate chunk with class context
                    header = f"class {node.name}:\n"
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            m_start = item.lineno
                            m_end = getattr(item, 'end_lineno', m_start + 10)
                            m_content = header + "\n".join(lines[m_start-1:m_end])
                            chunks.append(CodeChunk(m_content, "function", f"{node.name}.{item.name}", m_start, m_end, "python"))
                else:
                    chunks.append(CodeChunk(content, "class", node.name, start, end, "python"))
            
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno
                end = getattr(node, 'end_lineno', start + 20)
                content = "\n".join(lines[start-1:end])
                if len(content) > self.max_chars:
                    # Split large function with overlap
                    for sub in self.split_large(content, start, "python", node.name):
                        chunks.append(sub)
                else:
                    chunks.append(CodeChunk(content, "function", node.name, start, end, "python"))
        
        # If no structured chunks found, fallback
        if len(chunks) <= 1:
            return self.chunk_generic(text, "python")
        
        return chunks
    
    def chunk_generic(self, text: str, lang: str) -> List[CodeChunk]:
        """Smart generic chunker - respects boundaries"""
        lines = text.splitlines()
        chunks = []
        current = []
        current_len = 0
        start_line = 1
        
        for i, line in enumerate(lines, 1):
            current.append(line)
            current_len += len(line) + 1
            
            # Natural break points
            is_break = (
                current_len >= self.max_chars and
                (line.strip() == "" or 
                 line.strip().startswith(("}", ")", "]", "```", "---")) or
                 i == len(lines))
            )
            
            if is_break:
                content = "\n".join(current)
                chunks.append(CodeChunk(content, "generic", None, start_line, i, lang))
                # Overlap
                overlap_lines = current[-3:] if len(current) > 3 else []
                current = overlap_lines
                current_len = sum(len(l) for l in current)
                start_line = i - len(overlap_lines) + 1
        
        if current:
            content = "\n".join(current)
            chunks.append(CodeChunk(content, "generic", None, start_line, len(lines), lang))
        
        return chunks
    
    def split_large(self, content: str, start_line: int, lang: str, name: str = None) -> List[CodeChunk]:
        """Split large function/class into overlapping pieces by CHARS (not lines),
        breaking at line boundaries and preserving accurate line numbers."""
        chunks = []
        lines = content.splitlines(keepends=True)
        max_chars = self.max_chars
        overlap = self.overlap
        cur = []
        cur_len = 0
        s_line = start_line
        for line in lines:
            cur.append(line)
            cur_len += len(line)
            if cur_len >= max_chars:
                piece = "".join(cur)
                e_line = s_line + len(cur) - 1
                chunks.append(CodeChunk(piece, "function", name, s_line, e_line, lang))
                # Overlap: keep trailing lines covering ~`overlap` chars
                keep = []
                klen = 0
                for l in reversed(cur):
                    keep.insert(0, l)
                    klen += len(l)
                    if klen >= overlap:
                        break
                s_line = e_line - len(keep) + 1
                cur = keep
                cur_len = klen

        if cur:
            piece = "".join(cur)
            chunks.append(CodeChunk(piece, "function", name, s_line, s_line + len(cur) - 1, lang))
        return chunks
    
    def chunk_javascript(self, text: str) -> List[CodeChunk]:
        """AST-aware JavaScript/TypeScript chunking using tree-sitter"""
        if not TREE_SITTER_AVAILABLE:
            return self.chunk_generic(text, "javascript")
        
        try:
            import tree_sitter_javascript as tsjs
            import tree_sitter_typescript as tsts
            
            JS_LANGUAGE = Language(tsjs.language())
            TS_LANGUAGE = Language(tsts.language_typescript())
            
            parser = Parser()
            parser.language = JS_LANGUAGE
            
            tree = parser.parse(text.encode('utf-8'))
        except Exception:
            return self.chunk_generic(text, "javascript")
        
        chunks = []
        lines = text.splitlines()
        
        def get_node_text(node):
            return text[node.start_byte:node.end_byte]
        
        def extract_imports(node):
            imports = []
            for child in node.children:
                if child.type in ('import_statement', 'import_declaration'):
                    imports.append(child)
            return imports
        
        def extract_functions_classes(node, parent_class=None):
            results = []
            for child in node.children:
                if child.type in ('function_declaration', 'function_expression', 'arrow_function', 'method_definition'):
                    name_node = child.child_by_field_name('name')
                    name = get_node_text(name_node) if name_node else None
                    # For arrow functions assigned to variables, try to get name from parent
                    if name is None and child.type == 'arrow_function':
                        parent = child.parent
                        if parent and parent.type == 'variable_declarator':
                            name_node = parent.child_by_field_name('name')
                            name = get_node_text(name_node) if name_node else None
                        elif parent and parent.type == 'lexical_declaration':
                            # const/let arrow function
                            for decl in parent.children:
                                if decl.type == 'variable_declarator':
                                    name_node = decl.child_by_field_name('name')
                                    name = get_node_text(name_node) if name_node else None
                                    break
                    if parent_class and name:
                        name = f"{parent_class}.{name}"
                    results.append(('function', child, name))
                elif child.type in ('class_declaration', 'class_expression'):
                    name_node = child.child_by_field_name('name')
                    name = get_node_text(name_node) if name_node else None
                    results.append(('class', child, name))
                    # Recurse into class body for methods
                    body = child.child_by_field_name('body')
                    if body:
                        results.extend(extract_functions_classes(body, name))
                else:
                    results.extend(extract_functions_classes(child, parent_class))
            return results
        
        # Extract imports
        imports = extract_imports(tree.root_node)
        if imports:
            start = imports[0].start_point[0] + 1
            end = imports[-1].end_point[0] + 1
            content = "\n".join(lines[start-1:end])
            chunks.append(CodeChunk(content, "import", None, start, end, "javascript"))
        
        # Extract functions and classes
        for kind, node, name in extract_functions_classes(tree.root_node):
            start = node.start_point[0] + 1
            end = node.end_point[0] + 1
            content = "\n".join(lines[start-1:end])
            
            if len(content) > self.max_chars * 1.5:
                for sub in self.split_large(content, start, "javascript", name):
                    chunks.append(sub)
            else:
                chunks.append(CodeChunk(content, kind, name, start, end, "javascript"))
        
        if len(chunks) <= 1:
            return self.chunk_generic(text, "javascript")
        
        return chunks

    def chunk_typescript(self, text: str) -> List[CodeChunk]:
        """AST-aware TypeScript chunking using tree-sitter"""
        if not TREE_SITTER_AVAILABLE:
            return self.chunk_generic(text, "typescript")
        
        try:
            import tree_sitter_typescript as tsts
            
            TS_LANGUAGE = Language(tsts.language_typescript())
            TSX_LANGUAGE = Language(tsts.language_tsx())
            
            parser = Parser()
            parser.language = TS_LANGUAGE
            
            tree = parser.parse(text.encode('utf-8'))
        except Exception:
            return self.chunk_generic(text, "typescript")
        
        chunks = []
        lines = text.splitlines()
        
        def get_node_text(node):
            return text[node.start_byte:node.end_byte]
        
        def extract_imports(node):
            imports = []
            for child in node.children:
                if child.type in ('import_statement', 'import_declaration'):
                    imports.append(child)
            return imports
        
        def extract_functions_classes(node, parent_class=None):
            results = []
            for child in node.children:
                if child.type in ('function_declaration', 'function_expression', 'arrow_function', 'method_definition'):
                    name_node = child.child_by_field_name('name')
                    name = get_node_text(name_node) if name_node else None
                    # For arrow functions assigned to variables, try to get name from parent
                    if name is None and child.type == 'arrow_function':
                        parent = child.parent
                        if parent and parent.type == 'variable_declarator':
                            name_node = parent.child_by_field_name('name')
                            name = get_node_text(name_node) if name_node else None
                        elif parent and parent.type == 'lexical_declaration':
                            # const/let arrow function
                            for decl in parent.children:
                                if decl.type == 'variable_declarator':
                                    name_node = decl.child_by_field_name('name')
                                    name = get_node_text(name_node) if name_node else None
                                    break
                    if parent_class and name:
                        name = f"{parent_class}.{name}"
                    results.append(('function', child, name))
                elif child.type in ('class_declaration', 'class_expression', 'interface_declaration'):
                    name_node = child.child_by_field_name('name')
                    name = get_node_text(name_node) if name_node else None
                    results.append(('class', child, name))
                    body = child.child_by_field_name('body')
                    if body:
                        results.extend(extract_functions_classes(body, name))
                else:
                    results.extend(extract_functions_classes(child, parent_class))
            return results
        
        # Extract imports
        imports = extract_imports(tree.root_node)
        if imports:
            start = imports[0].start_point[0] + 1
            end = imports[-1].end_point[0] + 1
            content = "\n".join(lines[start-1:end])
            chunks.append(CodeChunk(content, "import", None, start, end, "typescript"))
        
        # Extract functions, classes, interfaces
        for kind, node, name in extract_functions_classes(tree.root_node):
            start = node.start_point[0] + 1
            end = node.end_point[0] + 1
            content = "\n".join(lines[start-1:end])
            
            if len(content) > self.max_chars * 1.5:
                for sub in self.split_large(content, start, "typescript", name):
                    chunks.append(sub)
            else:
                chunks.append(CodeChunk(content, kind, name, start, end, "typescript"))
        
        if len(chunks) <= 1:
            return self.chunk_generic(text, "typescript")
        
        return chunks

    def chunk(self, text: str, file_path: str) -> List[CodeChunk]:
        ext = Path(file_path).suffix.lower()
        if ext == ".py":
            return self.chunk_python(text)
        elif ext in (".js", ".jsx"):
            return self.chunk_javascript(text)
        elif ext in (".ts", ".tsx"):
            return self.chunk_typescript(text)
        else:
            lang = "javascript" if ext in (".js", ".ts", ".tsx") else "text"
            return self.chunk_generic(text, lang)

# Enhanced schema for v4 - hybrid search
V4_SCHEMA_SQL = """
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enhanced chunks with hybrid search + code graph
CREATE TABLE IF NOT EXISTS chunks_v4 (
    id SERIAL PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    file_path TEXT NOT NULL,
    chunk_index INT NOT NULL,
    chunk_type TEXT NOT NULL DEFAULT 'generic', -- function, class, import, generic
    chunk_name TEXT, -- function/class name
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    language TEXT,
    start_line INT,
    end_line INT,
    -- Vectors
    embedding vector(768) NOT NULL,
    -- Hybrid search: tsvector for keyword
    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    -- Code graph
    imports TEXT[], -- extracted imports
    calls TEXT[], -- function calls
    -- Metadata
    indexed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, file_path, chunk_index)
);

-- Code graph edges (file -> file dependencies)
CREATE TABLE IF NOT EXISTS code_graph (
    id SERIAL PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    source_file TEXT NOT NULL,
    target_file TEXT NOT NULL,
    relation TEXT NOT NULL, -- imports, calls, extends
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations memory (agent learns)
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL, -- user, assistant, tool
    content TEXT NOT NULL,
    tool_calls JSONB,
    project_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Long-term memory / lessons
CREATE TABLE IF NOT EXISTS memory (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL, -- pattern, lesson, preference, fact
    content TEXT NOT NULL,
    project_id TEXT,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for hybrid search
CREATE INDEX IF NOT EXISTS idx_chunks_v4_embedding ON chunks_v4 USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_chunks_v4_tsv ON chunks_v4 USING GIN (content_tsv);
CREATE INDEX IF NOT EXISTS idx_chunks_v4_trgm ON chunks_v4 USING GIN (content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_chunks_v4_project ON chunks_v4 (project_id, file_path);
-- NOTE: no ANN index on memory - it's small and HNSW gave unreliable approximate recall
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations (session_id, created_at);

-- Hybrid search function (RRF - Reciprocal Rank Fusion)
-- Better than linear scoring: no normalization needed, robust to outliers, parameter-free
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(768),
    match_count INT DEFAULT 10,
    rrf_k INT DEFAULT 60
) RETURNS TABLE (
    id INT,
    project_id TEXT,
    file_path TEXT,
    chunk_name TEXT,
    content TEXT,
    similarity FLOAT,
    rank FLOAT
) LANGUAGE plpgsql STABLE PARALLEL SAFE AS $$
DECLARE
    kw tsquery;
    candidate_k INT;
BEGIN
    -- Prepare full-text search query
    kw := websearch_to_tsquery('english', query_text);
    IF kw IS NULL OR kw = ''::tsquery THEN
        kw := plainto_tsquery('english', query_text);
    END IF;

    candidate_k := GREATEST(match_count * 8, 50);

    RETURN QUERY
    WITH vec_cand AS (
        -- 1. Rank top vector matches by order
        SELECT 
            v.id,
            (1 - (v.embedding <=> query_embedding))::FLOAT AS vec_sim,
            ROW_NUMBER() OVER (ORDER BY v.embedding <=> query_embedding) AS vec_rank
        FROM chunks_v4 v
        ORDER BY v.embedding <=> query_embedding
        LIMIT candidate_k
    ),
    kw_cand AS (
        -- 2. Rank top keyword matches by order
        SELECT 
            k.id,
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(k.content_tsv, kw) DESC) AS kw_rank
        FROM chunks_v4 k
        WHERE k.content_tsv @@ kw
        ORDER BY ts_rank_cd(k.content_tsv, kw) DESC
        LIMIT candidate_k
    ),
    combined AS (
        -- 3. Merge candidates and compute RRF score: 1/(k + rank)
        SELECT 
            COALESCE(v.id, k.id) AS cand_id,
            COALESCE(v.vec_sim, (1 - (c.embedding <=> query_embedding))::FLOAT) AS vec_sim,
            (
                COALESCE(1.0 / (rrf_k + v.vec_rank), 0.0) + 
                COALESCE(1.0 / (rrf_k + k.kw_rank), 0.0)
            )::FLOAT AS rrf_score
        FROM vec_cand v
        FULL OUTER JOIN kw_cand k ON v.id = k.id
        JOIN chunks_v4 c ON c.id = COALESCE(v.id, k.id)
    )
    SELECT
        c.id,
        c.project_id,
        c.file_path,
        c.chunk_name,
        c.content,
        cb.vec_sim AS similarity,
        cb.rrf_score AS rank
    FROM combined cb
    JOIN chunks_v4 c ON c.id = cb.cand_id
    ORDER BY cb.rrf_score DESC
    LIMIT match_count;
END;
$$;
"""
