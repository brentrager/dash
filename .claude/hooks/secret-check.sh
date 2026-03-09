#!/bin/bash
# Block commits that contain secrets in staged changes

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

# Only check on git commit commands
if ! echo "$COMMAND" | grep -q "git commit"; then
    exit 0
fi

# Scan staged diff for secrets
STAGED=$(git diff --cached --diff-filter=ACMR 2>/dev/null)

if [ -z "$STAGED" ]; then
    exit 0
fi

# Patterns that indicate leaked secrets
ISSUES=""

# Real API tokens/keys (long hex strings that aren't placeholders)
if echo "$STAGED" | grep -PE '(Bearer|Token|KEY|SECRET|PASSWORD)\s*[=:]\s*["'\''"]?[a-zA-Z0-9_\-]{32,}' | grep -vP '(\$\{|\$[A-Z]|your-|example|placeholder|xxx)' > /dev/null 2>&1; then
    ISSUES="$ISSUES\n- Possible API token or key found in staged changes"
fi

# Private keys
if echo "$STAGED" | grep -P 'BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY' | grep -v 'placeholder\|example\|your-\|\.\.\.' > /dev/null 2>&1; then
    ISSUES="$ISSUES\n- Private key found in staged changes"
fi

# Groq API keys
if echo "$STAGED" | grep -P 'gsk_[a-zA-Z0-9]{20,}' > /dev/null 2>&1; then
    ISSUES="$ISSUES\n- Groq API key found in staged changes"
fi

if [ -n "$ISSUES" ]; then
    echo "BLOCKED: Secrets detected in staged changes:$ISSUES"
    echo "Remove secrets before committing. Use env vars instead."
    exit 2
fi

exit 0
