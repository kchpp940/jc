#!/bin/bash
# Generate markdown document files (*.md)
# Requires the yapf python library
# use ./docgen all to generate all docs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
DOC2MD="$PROJECT_ROOT/doc2md.py"
DOCS_DIR="$PROJECT_ROOT/docs"
PARSERS_DOCS_DIR="$DOCS_DIR/parsers"

cd "$PROJECT_ROOT"

(
    echo Building docs for: package
    "$DOC2MD" jc > "$DOCS_DIR/readme.md" && echo "+++ package docs complete" || echo "*** PACKAGE DOCS FAILED ***"
) &

(
    echo Building docs for: lib
    "$DOC2MD" jc.lib > "$DOCS_DIR/lib.md" && echo "+++ lib docs complete" || echo "*** LIB DOCS FAILED ***"
) &

(
    echo Building docs for: utils
    "$DOC2MD" jc.utils > "$DOCS_DIR/utils.md" && echo "+++ utils docs complete" || echo "*** UTILS DOCS FAILED ***"
) &

(
    echo Building docs for: streaming
    "$DOC2MD" jc.streaming > "$DOCS_DIR/streaming.md" && echo "+++ streaming docs complete" || echo "*** STREAMING DOCS FAILED ***"
) &

(
    echo Building docs for: universal parser
    "$DOC2MD" jc.parsers.universal > "$PARSERS_DOCS_DIR/universal.md" && echo "+++ universal parser docs complete" || echo "*** UNIVERSAL PARSER DOCS FAILED ***"
) &

# get parser list using standardized metadata policy for documentation
parsers=()
while IFS= read -r parser_name; do
    [ -n "$parser_name" ] && parsers+=("$parser_name")
done < <(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from jc.metadata_policy import for_docs
for p in for_docs():
    print(p['name'])
")

for parser_name in "${parsers[@]}"; do
    {
        if [[ $1 == "all" ]] || ! git diff --quiet --exit-code HEAD~5 -- "jc/parsers/${parser_name}.py" 2>/dev/null; then
            echo "Building docs for: ${parser_name}"
            "$DOC2MD" jc.parsers."${parser_name}" > "$PARSERS_DOCS_DIR/${parser_name}.md" && echo "+++ ${parser_name} docs complete" || echo "*** ${parser_name} DOCS FAILED ***"
        fi
    } &
done
wait
echo "Document Generation Complete"
