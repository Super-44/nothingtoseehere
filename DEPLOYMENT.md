# Deployment Guide

This guide walks you through setting up CI/CD and publishing to PyPI.

## Prerequisites

1. **GitHub Repository**: Your code should be in a GitHub repository
2. **PyPI Account**: Create an account at https://pypi.org/account/register/
3. **TestPyPI Account** (optional but recommended): https://test.pypi.org/account/register/

## Step 1: Enable Trusted Publishing on PyPI

The workflow uses **Trusted Publishing** (OIDC) which is the modern, secure way to publish to PyPI without API tokens.

### For Production PyPI:

1. Go to https://pypi.org/manage/account/publishing/
2. Click "Add a new pending publisher"
3. Fill in:
   - **PyPI project name**: `nothingtoseehere`
   - **Owner**: Your GitHub username (e.g., `Super-44`)
   - **Repository name**: `nothingtoseehere` (or your repo name)
   - **Workflow filename**: `.github/workflows/publish.yml`
   - **Environment name**: `release` (must match the workflow)
4. Click "Add"

### For TestPyPI (optional):

1. Go to https://test.pypi.org/manage/account/publishing/
2. Follow the same steps as above

## Step 2: Create GitHub Environment

1. Go to your GitHub repository
2. Navigate to **Settings** → **Environments**
3. Click **New environment**
4. Name it: `release`
5. Click **Configure environment**
6. (Optional) Add protection rules if you want manual approval
7. Click **Save protection rules**

## Step 3: Test Locally

Before publishing, test the build locally:

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Check the built package
twine check dist/*

# (Optional) Test upload to TestPyPI
twine upload --repository testpypi dist/*
```

## Step 4: Create a Release

The workflow automatically publishes when you create a GitHub Release:

1. Go to your repository on GitHub
2. Click **Releases** → **Create a new release**
3. Choose a tag (e.g., `v1.0.0`) - create the tag if it doesn't exist
4. Fill in release title and description (you can copy from CHANGELOG.md)
5. Click **Publish release**

The workflow will:
1. Run tests on all Python versions
2. Build the package
3. Publish to PyPI automatically

## Step 5: Verify Publication

1. Check PyPI: https://pypi.org/project/nothingtoseehere/
2. Test installation:
   ```bash
   pip install nothingtoseehere
   ```

## Workflow Details

### Test Workflow (`.github/workflows/test.yml`)
- Runs on: Every push and pull request
- Tests on: Python 3.10, 3.11, 3.12, 3.13, 3.14
- Purpose: Ensure code quality before merging

### Publish Workflow (`.github/workflows/publish.yml`)
- Triggers on: GitHub Release creation
- Steps:
  1. **Test**: Runs full test suite
  2. **Build**: Creates wheel and source distribution
  3. **Publish**: Uploads to PyPI using trusted publishing

## Troubleshooting

### "Environment not found" error
- Make sure you created the `release` environment in GitHub Settings → Environments

### "Publisher not found" error
- Verify the trusted publisher is set up correctly on PyPI
- Check that the repository name and workflow filename match exactly

### "Package already exists" error
- You can't overwrite an existing version on PyPI
- Bump the version in `pyproject.toml` and create a new release

### Build fails
- Check that all dependencies are listed in `pyproject.toml`
- Verify `py.typed` file exists for type checking support
- Ensure README.md is in the root directory

## Manual Publishing (Alternative)

If you prefer to publish manually:

```bash
# Build
python -m build

# Upload to PyPI (requires API token)
twine upload dist/*
```

To get an API token:
1. Go to https://pypi.org/manage/account/token/
2. Create a new API token
3. Use it with: `twine upload -u __token__ -p <your-token> dist/*`

## Version Management

- Update version in `pyproject.toml` before each release
- Follow [Semantic Versioning](https://semver.org/):
  - `MAJOR.MINOR.PATCH` (e.g., `1.0.0`)
  - MAJOR: Breaking changes
  - MINOR: New features (backward compatible)
  - PATCH: Bug fixes

## Next Steps

After first publication:
- Add badges to README.md showing PyPI version and build status
- Consider adding a GitHub Actions badge
- Update documentation with installation instructions
