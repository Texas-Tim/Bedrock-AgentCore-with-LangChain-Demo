#!/bin/bash
# fix_otel_shebang.sh
# 
# Fixes hardcoded Python shebang paths in the cached dependencies.zip
# This is needed because `uv` packages scripts with the local venv's Python path,
# which doesn't exist on the AgentCore runtime.
#
# Usage: ./fix_otel_shebang.sh [agent_name]
#   agent_name: Optional. Defaults to 'langgraph_eval_agent'
#
# Run this AFTER `agentcore launch --force-rebuild-deps` and BEFORE the final deploy.

set -e

AGENT_NAME="${1:-strands_eval_agent}"
DEPS_DIR=".bedrock_agentcore/${AGENT_NAME}"
DEPS_ZIP="${DEPS_DIR}/dependencies.zip"

if [ ! -f "$DEPS_ZIP" ]; then
    echo "Error: $DEPS_ZIP not found"
    echo "Run 'agentcore launch --force-rebuild-deps' first to create the dependencies cache."
    exit 1
fi

echo "Fixing shebangs in $DEPS_ZIP..."

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Extract
unzip -q "$DEPS_ZIP" -d "$TEMP_DIR"

# Fix shebangs in bin/ scripts
FIXED_COUNT=0
for script in "$TEMP_DIR"/bin/*; do
    if [ -f "$script" ]; then
        # Check if it has the polyglot shebang pattern (#!/bin/sh followed by exec python)
        if head -3 "$script" | grep -q "exec.*python"; then
            # Extract the actual Python code (everything after the polyglot header)
            # The polyglot format is:
            #   #!/bin/sh
            #   '''exec' '/path/to/python' "$0" "$@"
            #   ' '''
            #   # -*- coding: utf-8 -*-
            #   <actual python code>
            
            # Create new file with proper shebang
            {
                echo '#!/usr/bin/env python3'
                # Skip the first 3 lines (polyglot header) and output the rest
                tail -n +4 "$script"
            } > "${script}.new"
            mv "${script}.new" "$script"
            chmod +x "$script"
            
            FIXED_COUNT=$((FIXED_COUNT + 1))
            echo "  Fixed: $(basename "$script")"
        fi
    fi
done

if [ $FIXED_COUNT -eq 0 ]; then
    echo "No scripts needed fixing."
    exit 0
fi

# Re-create the zip
rm "$DEPS_ZIP"
(cd "$TEMP_DIR" && zip -rq "../deps_fixed.zip" .)
mv "$(dirname "$TEMP_DIR")/deps_fixed.zip" "$DEPS_ZIP"

echo ""
echo "Fixed $FIXED_COUNT script(s)."
echo "Now run 'agentcore launch' (without --force-rebuild-deps) to deploy with the fixed dependencies."
