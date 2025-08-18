# GitHub Issue Auto Debug Script Usage Guide

## Overview

`github_issue_debug.py` is an automated script for:
1. Retrieving detailed information (title, body, comments, etc.) of a specified issue from the GitHub API.
2. Automatically uploading the GitHub repository to Prometheus.
3. Using Prometheus's AI analysis capabilities to debug the issue.
4. Returning analysis results, fix patches, etc.

## Prerequisites

### 1. Start Prometheus Service
Ensure the Prometheus service is running:
```bash
# Start using docker-compose
docker-compose -f docker-compose.win_mac.yml up -d

# Check service status
docker-compose -f docker-compose.win_mac.yml ps
```

### 2. Obtain GitHub Personal Access Token
1. Visit https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select the appropriate permission scope:
   - `repo` (access private repositories)
   - `public_repo` (access public repositories)
4. Generate and save the token.

### 3. Install Python Dependencies
```bash
pip install requests
```

## Basic Usage

### Simple Example
```bash
python github_issue_debug.py \
    --github-token "your_token_here" \
    --repo "owner/repository" \
    --issue-number 42
```

### Full Parameter Example
```bash
python github_issue_debug.py \
    --github-token "ghp_xxxxxxxxxxxxxxxxxxxx" \
    --repo "microsoft/vscode" \
    --issue-number 123 \
    --prometheus-url "http://localhost:8000" \
    --output-file "debug_result.json" \
    --run-build \
    --run-test \
    --push-to-remote \
    --image-name "python:3.11-slim" \
    --workdir "/app" \
    --build-commands "pip install -r requirements.txt" "python setup.py build" \
    --test-commands "pytest tests/" \
    --candidate-patches 3
```

## Parameter Details

### Required Parameters
- `--github-token`: GitHub Personal Access Token
- `--repo`: GitHub repository name in the format `owner/repo`
- `--issue-number`: Issue number to process

### Optional Parameters
- `--prometheus-url`: Prometheus service address (default: http://localhost:8000)
- `--output-file`: Path to the result output file (if not specified, output to console)

### Validation Options
- `--run-build`: Run build validation for the generated patch
- `--run-test`: Run test validation for the generated patch
- `--push-to-remote`: Push the fix to a remote Git branch

### Docker Environment Configuration
- `--dockerfile-content`: Specify Dockerfile content directly
- `--image-name`: Use a predefined Docker image
- `--workdir`: Working directory inside the container (default: /app)
- `--build-commands`: List of build commands
- `--test-commands`: List of test commands

### Other Options
- `--candidate-patches`: Number of candidate patches (default: 4)

## Usage Scenarios

### Scenario 1: Simple Bug Report Analysis
```bash
# Analyze a simple bug report without running any validation
python github_issue_debug.py \
    --github-token "your_token" \
    --repo "pytorch/pytorch" \
    --issue-number 89123
```

### Scenario 2: Python Project with Test Validation
```bash
# Perform a complete debug for a Python project, including build and test validation
python github_issue_debug.py \
    --github-token "your_token" \
    --repo "requests/requests" \
    --issue-number 5678 \
    --run-build \
    --run-test \
    --image-name "python:3.11-slim" \
    --build-commands "pip install -e ." \
    --test-commands "pytest tests/test_requests.py"
```

### Scenario 3: Node.js Project with Auto Push
```bash
# Process an issue for a Node.js project and automatically push the fix to a remote branch
python github_issue_debug.py \
    --github-token "your_token" \
    --repo "facebook/react" \
    --issue-number 9876 \
    --run-build \
    --run-test \
    --push-to-remote \
    --image-name "node:18-slim" \
    --build-commands "npm ci" "npm run build" \
    --test-commands "npm test"
```

### Scenario 4: Custom Docker Environment
```bash
# Use a custom Dockerfile for debugging
python github_issue_debug.py \
    --github-token "your_token" \
    --repo "tensorflow/tensorflow" \
    --issue-number 4321 \
    --run-build \
    --dockerfile-content "FROM tensorflow/tensorflow:latest-gpu
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt" \
    --workdir "/app" \
    --build-commands "python setup.py build_ext --inplace" \
    --test-commands "python -m pytest tests/unit/"
```

## Output Result Explanation

After execution, the script outputs results in JSON format, including the following fields:

```json
{
  "success": true,
  "issue_info": {
    "repo": "owner/repo",
    "number": 123,
    "title": "Issue Title",
    "url": "https://github.com/owner/repo/issues/123",
    "state": "open"
  },
  "prometheus_result": {
    "patch": "Generated code patch",
    "passed_reproducing_test": true,
    "passed_build": true,
    "passed_existing_test": false,
    "issue_response": "AI-generated issue response",
    "remote_branch_name": "prometheus-fix-issue-123"
  }
}
```

### Result Field Description
- `success`: Whether the process was successful
- `issue_info`: Basic information about the GitHub issue
- `prometheus_result.patch`: Code fix patch generated by Prometheus
- `prometheus_result.passed_*`: Status of various validations
- `prometheus_result.issue_response`: AI-generated issue analysis and response
- `prometheus_result.remote_branch_name`: Name of the remote branch pushed (if enabled)

## Common Issues and Solutions

### 1. GitHub API Limitations
**Problem**: Encountering API limit errors
**Solution**: 
- Ensure a valid Personal Access Token is used
- Check the token's permission scope
- Be mindful of GitHub API rate limits

### 2. Prometheus Service Connection Failure
**Problem**: Unable to connect to the Prometheus service
**Solution**:
```bash
# Check service status
docker-compose -f docker-compose.win_mac.yml ps

# Restart the service
docker-compose -f docker-compose.win_mac.yml restart

# Check logs
docker-compose -f docker-compose.win_mac.yml logs prometheus
```

### 3. Repository Upload Failure
**Problem**: Unable to access private repositories
**Solution**:
- Ensure the GitHub token has `repo` permissions
- Check if the repository URL format is correct
- For private repositories, ensure the token owner has access permissions

### 4. Build/Test Failure
**Problem**: Build or test failure in the Docker environment
**Solution**:
- Check if the specified Docker image is correct
- Validate the build and test commands
- Ensure the working directory is set correctly
- Check Prometheus logs for detailed error information

## Advanced Usage Tips

### 1. Batch Processing Multiple Issues
Create a batch script:
```bash
#!/bin/bash
GITHUB_TOKEN="your_token"
REPO="owner/repo"

for issue in 123 124 125; do
    echo "Processing issue #$issue"
    python github_issue_debug.py \
        --github-token "$GITHUB_TOKEN" \
        --repo "$REPO" \
        --issue-number $issue \
        --output-file "results/issue_${issue}_result.json"
done
```

### 2. Integration into CI/CD
Use in GitHub Actions:
```yaml
- name: Debug Issue with Prometheus
  run: |
    python github_issue_debug.py \
      --github-token "${{ secrets.GITHUB_TOKEN }}" \
      --repo "${{ github.repository }}" \
      --issue-number "${{ github.event.issue.number }}" \
      --output-file "debug_result.json"
```

### 3. Post-Processing Results
Process results using Python:
```python
import json

with open('debug_result.json', 'r') as f:
    result = json.load(f)

if result['success']:
    patch = result['prometheus_result']['patch']
    # Further process the patch...
```

## Notes

1. **Security**: 
   - Do not hardcode the GitHub token in the code
   - Use environment variables or configuration files to store sensitive information

2. **Performance**:
   - Processing large repositories may take a long time
   - It is recommended to test on smaller repositories first

3. **Resource Usage**:
   - Ensure sufficient disk space for cloning repositories
   - Monitor Docker container resource usage

4. **Network**:
   - Ensure a stable network connection
   - Some network environments may require proxy configuration

## Troubleshooting

### Enable Detailed Logs
Set environment variables to enable detailed output:
```bash
export PYTHONUNBUFFERED=1
python github_issue_debug.py --your-args
```

### Check Prometheus Status
```bash
# Check API health status
curl http://localhost:8000/docs

# Check knowledge graph status
curl http://localhost:8000/repository/exists/
```

### Reset Prometheus State
If you need to start over:
```bash
# Delete existing knowledge graph
curl -X GET http://localhost:8000/repository/delete/
```
