# Heimdall setup - run in X:\second-brain-kb

# 1. Install heimdall globally (needs Node >=22.5)
npm i -g @arihantdeva/heimdall

# 2. Wire into your harnesses
heimdall init --harness opencode
heimdall init --harness claude-code
heimdall init --harness cursor
heimdall init --detect

# 3. Build graft backend (for ranked search + doctor)
# From https://github.com/redmountain-git/heimdall#quickstart
# Requires Rust + cargo
# git clone https://github.com/redmountain-git/graft
# cd graft && cargo build --release
# cp target/release/graft ~/.cargo/bin/ or add to PATH

# Then:
heimdall doctor  # should print HEALTHY
heimdall search "excel tracker portfolio optimization"

# 4. Use with your second-brain
# Our ingest_heimdall.py now uses same tree-sitter chunking as heimdall
# Zero token, CPU-only, symbol-level (L2) instead of tiktoken 1000 chars
# Verified hits: STRONG/WEAK/REBUILT/STALE
