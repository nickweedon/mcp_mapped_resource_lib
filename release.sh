#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to get current version from pyproject.toml
get_current_version() {
    grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'
}

# Function to get latest version from git tags
get_latest_tag_version() {
    # Get all tags matching vX.Y.Z pattern, sort them, and get the latest
    local latest_tag=$(git tag --list 'v[0-9]*.[0-9]*.[0-9]*' | sort -V | tail -n 1)

    if [ -z "$latest_tag" ]; then
        # No tags found, use version from pyproject.toml
        get_current_version
    else
        # Strip the 'v' prefix
        echo "${latest_tag#v}"
    fi
}

# Function to increment patch version
increment_patch_version() {
    local version="$1"
    local major minor patch

    # Parse version into components
    IFS='.' read -r major minor patch <<< "$version"

    # Increment patch version
    patch=$((patch + 1))

    echo "${major}.${minor}.${patch}"
}

# Check if version argument is provided, if not auto-increment
if [ $# -eq 0 ]; then
    # Use latest git tag version, not pyproject.toml
    CURRENT_VERSION=$(get_latest_tag_version)
    VERSION=$(increment_patch_version "$CURRENT_VERSION")
    print_info "No version specified, auto-incrementing from latest tag: ${CURRENT_VERSION} → ${VERSION}"
elif [ $# -eq 1 ]; then
    VERSION="$1"
else
    print_error "Usage: ./release.sh [version]"
    echo "Examples:"
    echo "  ./release.sh           # Auto-increment patch version (0.1.0 → 0.1.1)"
    echo "  ./release.sh 0.2.0     # Specify version explicitly"
    exit 1
fi

TAG="v${VERSION}"

# Validate version format (basic semver: X.Y.Z)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    print_error "Invalid version format: $VERSION"
    echo "Version must be in semver format (e.g., 0.2.0, 1.0.0, 2.1.3)"
    exit 1
fi

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI (gh) is not installed"
    echo "Install it from: https://cli.github.com/"
    echo "Or run: brew install gh (macOS) / sudo apt install gh (Ubuntu)"
    exit 1
fi

# Check if gh is authenticated
if ! gh auth status &> /dev/null; then
    print_error "GitHub CLI is not authenticated"
    echo "Run: gh auth login"
    exit 1
fi

# Check if working directory is clean
if ! git diff-index --quiet HEAD --; then
    print_error "Working directory has uncommitted changes"
    echo "Please commit or stash your changes before releasing"
    git status --short
    exit 1
fi

echo ""
print_info "Preparing release ${TAG}..."
echo ""

# Update version in pyproject.toml
print_info "Updating version in pyproject.toml to ${VERSION}..."
sed -i "s/^version = .*/version = \"${VERSION}\"/" pyproject.toml

if ! grep -q "version = \"${VERSION}\"" pyproject.toml; then
    print_error "Failed to update version in pyproject.toml"
    exit 1
fi

print_success "Version updated in pyproject.toml"
echo ""

# Run all tests to verify everything passes
print_info "Running tests (make all)..."
echo ""

if ! make all; then
    print_error "Tests failed! Aborting release."
    echo ""
    print_info "Reverting version change..."
    git checkout pyproject.toml
    exit 1
fi

echo ""
print_success "All tests passed!"
echo ""

# Commit version bump
print_info "Committing version bump..."
git add pyproject.toml
git commit -m "Bump version to ${VERSION}"
print_success "Version bump committed"
echo ""

# Create git tag
print_info "Creating git tag ${TAG}..."
git tag -a "${TAG}" -m "Release ${VERSION}"
print_success "Tag ${TAG} created"
echo ""

# Push to GitHub
print_info "Pushing to GitHub..."
git push origin main
git push origin "${TAG}"
print_success "Pushed to GitHub"
echo ""

# Create GitHub release with auto-generated notes
print_info "Creating GitHub release..."
gh release create "${TAG}" --generate-notes

echo ""
print_success "Release ${TAG} created successfully!"
echo ""
print_info "Next steps:"
echo "  1. GitHub Actions will automatically publish to PyPI"
echo "  2. Check the workflow at: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
echo "  3. Verify PyPI package at: https://pypi.org/project/mcp-mapped-resource-lib/"
echo ""
