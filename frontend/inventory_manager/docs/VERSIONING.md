# Semantic Versioning Guide

## Overview

This project follows **[Semantic Versioning 2.0.0](https://semver.org/)** (SemVer).

**Version Format**: `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)

---

## 📌 Versioning Rules

Given a version number `MAJOR.MINOR.PATCH`:

1. **MAJOR** version when you make incompatible API changes
2. **MINOR** version when you add functionality in a backward compatible manner
3. **PATCH** version when you make backward compatible bug fixes

### Pre-release Versions

For pre-production releases:
- `1.0.0-alpha.1` - Alpha release (internal testing)
- `1.0.0-beta.1` - Beta release (external testing)
- `1.0.0-rc.1` - Release candidate

---

## 🎯 Version Increment Decision Tree

```
┌─ Breaking change? (API/behavior incompatible with previous version)
│  └─ YES → Increment MAJOR (e.g., 1.2.3 → 2.0.0)
│
├─ New feature? (backward compatible functionality)
│  └─ YES → Increment MINOR (e.g., 1.2.3 → 1.3.0)
│
└─ Bug fix only? (backward compatible fix)
   └─ YES → Increment PATCH (e.g., 1.2.3 → 1.2.4)
```

---

## 📋 What Counts as Breaking?

### ❌ Breaking Changes (MAJOR bump required):

- **API Changes**:
  - Removing or renaming public functions/classes
  - Changing function signatures (parameters, return types)
  - Removing configuration options
  - Changing default behavior that users depend on

- **Data Schema**:
  - Google Sheets column renames/deletions
  - Database schema changes requiring migration
  - Changed data formats (CSV structure, JSON shape)

- **Dependencies**:
  - Dropping support for Python 3.11
  - Requiring new external services

- **Environment**:
  - New required environment variables
  - Changed deployment requirements

### ✅ Not Breaking (MINOR/PATCH allowed):

- Adding new optional parameters with defaults
- Adding new endpoints/routes
- Adding new columns to sheets (appended)
- Deprecation warnings (without removing functionality)
- Performance improvements
- Internal refactoring

---

## 🔢 Current Version Management

### Where Version Lives

**Primary Source of Truth**: `__version__.py`

```python
# __version__.py
__version__ = "1.0.0"
__version_info__ = (1, 0, 0)
```

**Referenced In**:
- `app.py` - Import and expose via `/version` endpoint
- `README.md` - Manually update badge
- `CHANGELOG.md` - Updated for each release
- Git tags - `v1.0.0` format

---

## 🚀 Release Process

### 1. Prepare Release

```bash
# Ensure you're on main and up to date
git checkout main
git pull origin main

# Create release branch
git checkout -b release/v1.2.0
```

### 2. Update Version

**Update `__version__.py`**:
```python
__version__ = "1.2.0"
__version_info__ = (1, 2, 0)
```

### 3. Update Changelog

**Add to `CHANGELOG.md`**:
```markdown
## [1.2.0] - 2025-10-10

### Added
- New low-stock alert email notifications
- CSV export with custom date ranges

### Changed
- Improved sync performance by 30%

### Fixed
- Fixed race condition in inventory reconciliation

### Security
- Updated requests library to patch CVE-2024-XXXX
```

### 4. Commit and Push

```bash
git add __version__.py CHANGELOG.md
git commit -m "chore: bump version to 1.2.0"
git push origin release/v1.2.0
```

### 5. Create Pull Request

- Title: `release: v1.2.0`
- Use release PR template
- Request review from @HEAD_DEVELOPER

### 6. Merge and Tag

After PR approval:

```bash
# Merge to main (via GitHub UI - squash merge)

# Pull latest main
git checkout main
git pull origin main

# Create and push tag
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0
```

### 7. GitHub Release (Automated)

The `release.yml` workflow automatically:
1. Detects the `v*` tag
2. Drafts a GitHub Release
3. Attaches changelog notes
4. Uploads test reports and coverage

**You just need to**:
1. Go to GitHub Releases
2. Review the draft
3. Click "Publish release"

---

## 🤖 Automated Versioning (Future)

### Option A: Conventional Commits + Automation

Use commit message format to auto-determine version:

- `feat: ...` → MINOR bump
- `fix: ...` → PATCH bump
- `feat!: ...` or `BREAKING CHANGE:` → MAJOR bump

**Tools**: [semantic-release](https://github.com/semantic-release/semantic-release)

### Option B: PR Labels

Label PRs with:
- `breaking` → MAJOR
- `feature` → MINOR
- `bugfix` → PATCH

**Tools**: [release-drafter](https://github.com/release-drafter/release-drafter)

---

## 📅 Release Cadence

### Recommended Schedule:

- **MAJOR**: 6-12 months (when necessary)
- **MINOR**: Monthly (feature releases)
- **PATCH**: Weekly or as-needed (bug fixes, security)

### Hotfix Process:

For critical production bugs:

```bash
# Branch from tagged release
git checkout -b hotfix/v1.2.1 v1.2.0

# Make minimal fix
# ... edit files ...

# Update version to 1.2.1
# Update CHANGELOG.md

# Commit, PR, merge, tag
git commit -am "fix: critical inventory sync bug"
# ... PR process ...
git tag v1.2.1
git push origin v1.2.1
```

---

## 📊 Version History

| Version | Date | Type | Highlights |
|---------|------|------|------------|
| 0.1.0 | 2025-10-01 | Initial | First working prototype |
| 0.2.0 | 2025-10-05 | Minor | Added Lightspeed sync |
| 1.0.0 | 2025-10-10 | Major | Production-ready release |

---

## 🔍 Checking Current Version

### Via API:
```bash
curl http://localhost:8000/version
# {"version": "1.0.0"}
```

### Via Python:
```python
from app import __version__
print(__version__)
```

### Via Git:
```bash
git describe --tags --abbrev=0
# v1.0.0
```

---

## 🏷️ Tagging Guidelines

### Tag Format:
- Use `v` prefix: `v1.2.3`
- Annotated tags (not lightweight): `git tag -a v1.2.3 -m "Release 1.2.3"`
- Tag messages should summarize key changes

### Signing Tags (Recommended):
```bash
git tag -s v1.2.3 -m "Release 1.2.3"
# Requires GPG key configured
```

---

## 🐛 Pre-release Workflow

For testing before official release:

```bash
# Create pre-release
git tag v1.3.0-beta.1
git push origin v1.3.0-beta.1

# Test in staging environment

# If issues found, create beta.2
git tag v1.3.0-beta.2

# When stable, release
git tag v1.3.0
```

**GitHub Release**: Mark pre-releases with "This is a pre-release" checkbox

---

## 📝 Deprecation Policy

When removing features:

1. **MINOR version**: Add deprecation warning
   ```python
   warnings.warn("Function X is deprecated, use Y instead", DeprecationWarning)
   ```

2. **Next MAJOR version**: Remove deprecated feature
   - Document in CHANGELOG under `### Removed`
   - Provide migration guide

**Minimum Deprecation Period**: 1 MINOR release cycle

---

## 🔐 Security Releases

For security fixes:

1. **Patch existing versions** if still supported
2. **Use SECURITY.md process** for disclosure
3. **Tag with `[SECURITY]` in CHANGELOG**
4. **Notify users** via release notes

Example:
```markdown
## [1.2.4] - 2025-10-15

### Security
- **[SECURITY]** Fixed SQL injection in inventory search (CVE-2025-XXXX)
- Updated dependencies with known vulnerabilities
```

---

## ❓ FAQ

**Q: Do I need to bump version for every commit?**  
A: No. Version bumps happen at release time, not per commit.

**Q: What if I merge multiple features before releasing?**  
A: That's fine. One release can include multiple features (still a MINOR bump).

**Q: Can I skip versions?**  
A: Yes. You can go from 1.2.3 → 1.5.0 if you want. SemVer doesn't require sequential.

**Q: Should I update README version badge manually?**  
A: Yes, or automate it with a release script.

**Q: What about `0.x.x` versions?**  
A: `0.x.x` is for initial development. Anything goes. Breaking changes are OK in MINOR bumps.

---

## 📚 References

- **Semantic Versioning Spec**: https://semver.org/
- **Keep a Changelog**: https://keepachangelog.com/
- **Conventional Commits**: https://www.conventionalcommits.org/

---

**Version**: 1.0  
**Last Updated**: 2025-10-10  
**Next Review**: After 5 releases
