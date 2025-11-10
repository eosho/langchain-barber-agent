# GitHub Actions Setup Guide

## Overview

The project includes three GitHub Actions workflows for automated testing, security scanning, and deployment.

## Workflows

### 1. CI (Continuous Integration)
**File**: `.github/workflows/ci.yml`  
**Triggers**: Push to main/develop, Pull Requests

**Jobs**:
- **Lint & Format**: Ruff and Black code quality checks
- **Type Check**: MyPy static type analysis
- **Test**: Unit and integration tests (Python 3.11 & 3.12)
- **Security**: Bandit security scanning
- **Build**: Package build verification

**Required Secrets**: None (optional: `OPENAI_API_KEY` for tests)

### 2. CD (Continuous Deployment)
**File**: `.github/workflows/cd.yml`  
**Triggers**: Version tags (`v*.*.*`), Manual dispatch

**Jobs**:
- **Build & Push**: Docker image to GitHub Container Registry
- **Deploy Staging**: Auto-deploy to staging (on develop branch)
- **Deploy Production**: Deploy to production (requires approval)
- **Release**: Create GitHub release with changelog
- **Notify**: Send deployment notifications

**Required Secrets**:
- `GITHUB_TOKEN` (auto-provided)
- Optional: `SLACK_WEBHOOK` for notifications

### 3. CodeQL Security Scan
**File**: `.github/workflows/codeql.yml`  
**Triggers**: Push, Pull Requests, Weekly schedule

**Jobs**:
- **Analyze**: Security vulnerability scanning with CodeQL

## Setup Instructions

### 1. Enable GitHub Actions

1. Go to repository **Settings** → **Actions** → **General**
2. Set **Actions permissions** to "Allow all actions"
3. Enable **Read and write permissions** for GITHUB_TOKEN

### 2. Configure Secrets

Add secrets in **Settings** → **Secrets and variables** → **Actions**:

```
OPENAI_API_KEY=sk-...        # Optional: for tests
SLACK_WEBHOOK=https://...     # Optional: for notifications
```

### 3. Configure Environments

Create environments for deployment:

1. Go to **Settings** → **Environments**
2. Create **staging** environment
3. Create **production** environment with protection rules:
   - Required reviewers: 1+
   - Wait timer: 0 minutes
   - Deployment branches: Only protected branches

### 4. Enable CodeQL

1. Go to **Security** → **Code scanning**
2. Click **Set up code scanning** → **GitHub Actions**
3. Commit the `.github/workflows/codeql.yml` file

### 5. Enable Branch Protection

Recommended rules for `main` branch:

1. Go to **Settings** → **Branches** → **Add rule**
2. Branch name pattern: `main`
3. Enable:
   - Require status checks before merging
     - Required checks: `lint`, `type-check`, `test`
   - Require pull request before merging
   - Require conversation resolution before merging
   - Do not allow bypassing the above settings

## Usage

### Running CI

CI runs automatically on:
- Every push to `main` or `develop`
- Every pull request to `main` or `develop`

**Skip CI**: Add `[skip ci]` to commit message

### Triggering Deployment

**Deploy via Git Tag**:
```bash
# Create version tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

**Manual Deployment**:
1. Go to **Actions** → **CD**
2. Click **Run workflow**
3. Select environment (staging/production)
4. Click **Run workflow**

### Monitoring

View workflow runs:
- **Actions** tab → Select workflow
- Click on a run to see job details
- Download artifacts (build, test coverage, security reports)

## Customization

### Modify CI Jobs

Edit `.github/workflows/ci.yml`:

```yaml
# Add new job
custom-check:
  name: Custom Check
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Run custom script
      run: ./scripts/custom-check.sh
```

### Add Deployment Target

Edit `.github/workflows/cd.yml`:

```yaml
deploy-aws:
  name: Deploy to AWS
  runs-on: ubuntu-latest
  needs: build-and-push
  steps:
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Deploy to ECS
      run: |
        # Your deployment commands
```

### Add Notifications

Edit `.github/workflows/cd.yml` notify job:

```yaml
- name: Slack notification
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## Troubleshooting

### Tests Failing

- Check test logs in Actions tab
- Ensure database is properly initialized
- Verify environment variables are set

### Deployment Failing

- Check deployment logs
- Verify secrets are configured
- Ensure environment exists and has proper permissions

### CodeQL Failing

- Review security alerts in Security tab
- Fix vulnerabilities in code
- Update dependencies if needed

## Best Practices

1. **Always run tests locally** before pushing
2. **Use pre-commit hooks** to catch issues early
3. **Review CI logs** for warnings even if tests pass
4. **Monitor security alerts** regularly
5. **Keep dependencies updated** with Dependabot
6. **Use semantic versioning** for releases (v1.0.0, v1.1.0, etc.)
7. **Write meaningful commit messages** for better changelogs
8. **Test in staging** before production deployment

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Hub](https://hub.docker.com/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
