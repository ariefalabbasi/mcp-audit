#!/bin/bash
# ============================================================================
# Validate Public Sync
# ============================================================================
# Validates that a synced public directory:
# 1. Contains all required files
# 2. Does NOT contain any internal files
# 3. Is a valid Python package
# ============================================================================

set -e

PUBLIC_DIR="${1:-.}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Validating public sync: $PUBLIC_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ERRORS=0

# Check required files exist
echo ""
echo "📁 Checking required files..."
REQUIRED_FILES=(
  "src/mcp_audit/__init__.py"
  "src/mcp_audit/cli.py"
  "pyproject.toml"
  "README.md"
  "LICENSE"
  "CHANGELOG.md"
  "CONTRIBUTING.md"
  "mcp-audit.toml"
  "docs/platforms/claude-code.md"
  ".github/workflows/ci.yml"
)

for file in "${REQUIRED_FILES[@]}"; do
  if [ -f "$PUBLIC_DIR/$file" ]; then
    echo "  ✅ $file"
  else
    echo "  ❌ MISSING: $file"
    ERRORS=$((ERRORS + 1))
  fi
done

# Check internal files are excluded
echo ""
echo "🔒 Checking internal files excluded..."
INTERNAL_PATTERNS=(
  "backlog"
  "quickref"
  "CLAUDE.md"
  ".claude"
  ".envrc"
  ".claude-settings.json"
  ".inst_id"
  "docs/ideas"
  "docs/LOG-FORMAT-REVIEW.md"
  ".public-exclude"
  ".github/workflows/auto-tag.yml"
  ".github/workflows/publish.yml"
)

for pattern in "${INTERNAL_PATTERNS[@]}"; do
  if [ -e "$PUBLIC_DIR/$pattern" ]; then
    echo "  ❌ SHOULD NOT EXIST: $pattern"
    ERRORS=$((ERRORS + 1))
  else
    echo "  ✅ Excluded: $pattern"
  fi
done

# Validate Python package
echo ""
echo "🐍 Validating Python package..."
cd "$PUBLIC_DIR"

if python3 -c "import sys; sys.path.insert(0, 'src'); import mcp_audit" 2>/dev/null; then
  echo "  ✅ Package imports successfully"
else
  echo "  ❌ Package import failed"
  ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ]; then
  echo "✅ Validation PASSED"
  exit 0
else
  echo "❌ Validation FAILED ($ERRORS errors)"
  exit 1
fi
