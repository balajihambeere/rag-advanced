# debug_retrieval.py
# Standalone retrieval debugger — no HTTP server, no timeout.
# Run: python debug_retrieval.py
# Add breakpoint() anywhere here or inside retrieval/ or pipeline/ modules to step with pdb.
# VS Code: open this file, set gutter breakpoints, press F5 (uses .vscode/launch.json).

from dotenv import load_dotenv
load_dotenv()

from retrieval.entry import retrieve_with_optional_hyde

QUERY = "show me something nice for the rains"

chunks = retrieve_with_optional_hyde(QUERY)

print(f"\nQuery: {QUERY}")
print(f"chunks returned: {len(chunks)}\n")
for i, c in enumerate(chunks):
    print(f"[{i}] {c.text[:200]}")
    print()
