#!/usr/bin/env python3
"""
GitHub Issue Auto Debug Script

This script automatically retrieves issue information from GitHub, uploads the repository to Prometheus, and sends the issue for debug analysis.

Usage:
    python github_issue_debug.py --github-token YOUR_TOKEN --repo owner/repo --issue-number 42

Parameter Description:
    --github-token: GitHub Personal Access Token (required)
    --repo: GitHub repository (format: owner/repo) (required)
    --issue-number: Issue number (required)
    --prometheus-url: Prometheus service address (default: http://localhost:8000)
    --output-file: Result output file (optional, default outputs to console)
    --run-build: Whether to run build validation (default: False)
    --run-test: Whether to run test validation (default: False)
    --push-to-remote: Whether to push the fix to a remote branch (default: False)
"""

import argparse
import json
import sys
from typing import Dict
from urllib.parse import urljoin

import requests


class GitHubIssueDebugger:
    def __init__(self, github_token: str, prometheus_url: str = "http://localhost:8000"):
        """
        Initialize GitHub Issue Debugger

        Args:
            github_token: GitHub Personal Access Token
            prometheus_url: Prometheus service URL
        """
        self.github_token = github_token
        self.prometheus_url = prometheus_url.rstrip("/")
        self.github_headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.prometheus_headers = {"Content-Type": "application/json"}

    def get_github_issue(self, repo: str, issue_number: int) -> Dict:
        """
        Retrieve issue information from GitHub

        Args:
            repo: Repository name (format: owner/repo)
            issue_number: Issue number

        Returns:
            A dictionary containing issue information
        """
        print(f"Retrieving GitHub issue: {repo}#{issue_number}")

        # Retrieve basic issue information
        issue_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
        response = requests.get(issue_url, headers=self.github_headers)

        if response.status_code != 200:
            raise Exception(f"Failed to retrieve issue: {response.status_code} - {response.text}")

        issue_data = response.json()

        # Retrieve issue comments
        comments_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
        comments_response = requests.get(comments_url, headers=self.github_headers)

        comments = []
        if comments_response.status_code == 200:
            comments_data = comments_response.json()
            comments = [
                {"username": comment["user"]["login"], "comment": comment["body"]}
                for comment in comments_data
            ]

        return {
            "number": issue_data["number"],
            "title": issue_data["title"],
            "body": issue_data["body"] or "",
            "comments": comments,
            "state": issue_data["state"],
            "html_url": issue_data["html_url"],
        }

    def upload_repository_to_prometheus(self, repo: str) -> bool:
        """
        Upload GitHub repository to Prometheus

        Args:
            repo: Repository name (format: owner/repo)

        Returns:
            Whether the upload was successful
        """
        print(f"Uploading repository to Prometheus: {repo}")

        # Construct GitHub HTTPS URL
        github_url = f"https://github.com/{repo}.git"

        # Call Prometheus API to upload repository
        upload_url = urljoin(self.prometheus_url, "/repository/github/")
        params = {"https_url": github_url}

        response = requests.get(upload_url, params=params, headers=self.prometheus_headers)

        if response.status_code == 200:
            print("Repository uploaded successfully")
            return True
        else:
            print(f"Failed to upload repository: {response.status_code} - {response.text}")
            return False

    def check_repository_exists(self) -> bool:
        """
        Check if the knowledge graph already exists in Prometheus

        Returns:
            Whether the knowledge graph exists
        """
        exists_url = urljoin(self.prometheus_url, "/repository/exists/")
        response = requests.get(exists_url, headers=self.prometheus_headers)

        if response.status_code == 200:
            return response.json()
        return False

    def send_issue_to_prometheus(self, issue_data: Dict, config: Dict) -> Dict:
        """
        Send issue to Prometheus for debugging

        Args:
            issue_data: GitHub issue data
            config: Configuration parameters

        Returns:
            Response from Prometheus
        """
        print("Sending issue to Prometheus for debug analysis...")

        # Construct Prometheus API request data
        request_data = {
            "issue_number": issue_data["number"],
            "issue_title": issue_data["title"],
            "issue_body": issue_data["body"],
            "issue_comments": issue_data["comments"],
            "issue_type": "bug",
            "run_build": config.get("run_build", False),
            "run_existing_test": config.get("run_test", False),
            "number_of_candidate_patch": config.get("candidate_patches", 4),
            "push_to_remote": config.get("push_to_remote", False),
        }

        # Add Docker configuration if present
        if config.get("dockerfile_content"):
            request_data["dockerfile_content"] = config["dockerfile_content"]
            request_data["workdir"] = config.get("workdir", "/app")
        elif config.get("image_name"):
            request_data["image_name"] = config["image_name"]
            request_data["workdir"] = config.get("workdir", "/app")

        if config.get("build_commands"):
            request_data["build_commands"] = config["build_commands"]

        if config.get("test_commands"):
            request_data["test_commands"] = config["test_commands"]

        # Send request to Prometheus
        answer_url = urljoin(self.prometheus_url, "/issue/answer/")
        response = requests.post(answer_url, json=request_data, headers=self.prometheus_headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Prometheus processing failed: {response.status_code} - {response.text}"
            )

    def process_issue(self, repo: str, issue_number: int, config: Dict) -> Dict:
        """
        Complete issue processing workflow

        Args:
            repo: Repository name
            issue_number: Issue number
            config: Configuration parameters

        Returns:
            Processing result
        """
        try:
            # 1. Retrieve GitHub issue
            issue_data = self.get_github_issue(repo, issue_number)

            # 2. Check if repository is already uploaded, if not, upload it
            if not self.check_repository_exists():
                if not self.upload_repository_to_prometheus(repo):
                    raise Exception("Repository upload failed")
            else:
                print("Knowledge graph already exists in Prometheus, skipping repository upload")

            # 3. Send issue to Prometheus for debugging
            result = self.send_issue_to_prometheus(issue_data, config)

            # 4. Integrate results
            return {
                "success": True,
                "issue_info": {
                    "repo": repo,
                    "number": issue_data["number"],
                    "title": issue_data["title"],
                    "url": issue_data["html_url"],
                    "state": issue_data["state"],
                },
                "prometheus_result": result,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "issue_info": {"repo": repo, "number": issue_number},
            }


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Issue Auto Debug Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--github-token", required=True, help="GitHub Personal Access Token")

    parser.add_argument("--repo", required=True, help="GitHub repository (format: owner/repo)")

    parser.add_argument("--issue-number", type=int, required=True, help="Issue number")

    parser.add_argument(
        "--prometheus-url",
        default="http://localhost:9002",
        help="Prometheus service address (default: http://localhost:9002)",
    )

    parser.add_argument(
        "--output-file",
        help="Path to the result output file (optional, default outputs to console)",
    )

    parser.add_argument("--run-build", action="store_true", help="Run build validation")

    parser.add_argument("--run-test", action="store_true", help="Run test validation")

    parser.add_argument("--push-to-remote", action="store_true", help="Push fix to remote branch")

    parser.add_argument(
        "--dockerfile-content", help="Dockerfile content (for specifying container environment)"
    )

    parser.add_argument(
        "--image-name", help="Docker image name (for specifying container environment)"
    )

    parser.add_argument(
        "--workdir",
        default="/app",
        help="Working directory (required when using container environment)",
    )

    parser.add_argument("--build-commands", nargs="+", help="List of build commands")

    parser.add_argument("--test-commands", nargs="+", help="List of test commands")

    parser.add_argument(
        "--candidate-patches", type=int, default=4, help="Number of candidate patches (default: 4)"
    )

    args = parser.parse_args()

    # Validate repo format
    if "/" not in args.repo:
        print("Error: Invalid repo format, should be 'owner/repo'")
        sys.exit(1)

    # Build configuration
    config = {
        "run_build": args.run_build,
        "run_test": args.run_test,
        "push_to_remote": args.push_to_remote,
        "candidate_patches": args.candidate_patches,
        "workdir": args.workdir,
    }

    if args.dockerfile_content:
        config["dockerfile_content"] = args.dockerfile_content

    if args.image_name:
        config["image_name"] = args.image_name

    if args.build_commands:
        config["build_commands"] = args.build_commands

    if args.test_commands:
        config["test_commands"] = args.test_commands

    # Create debugger and process issue
    debugger = GitHubIssueDebugger(args.github_token, args.prometheus_url)
    result = debugger.process_issue(args.repo, args.issue_number, config)

    # Output results
    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Results saved to: {args.output_file}")
    else:
        print("\n" + "=" * 60)
        print("Processing Results:")
        print("=" * 60)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    # Simplified summary output
    print("\n" + "=" * 60)
    print("Execution Summary:")
    print("=" * 60)

    if result["success"]:
        issue_info = result["issue_info"]
        prometheus_result = result["prometheus_result"]

        print("✅ Successfully processed GitHub Issue")
        print(f"   Repository: {issue_info['repo']}")
        print(f"   Issue: #{issue_info['number']} - {issue_info['title']}")
        print(f"   URL: {issue_info['url']}")
        print(f"   State: {issue_info['state']}")

        if prometheus_result.get("patch"):
            print("✅ Generated fix patch")

        if prometheus_result.get("passed_build") is not None:
            status = "✅ Passed" if prometheus_result["passed_build"] else "❌ Failed"
            print(f"   Build Validation: {status}")

        if prometheus_result.get("passed_existing_test") is not None:
            status = "✅ Passed" if prometheus_result["passed_existing_test"] else "❌ Failed"
            print(f"   Test Validation: {status}")

        if prometheus_result.get("remote_branch_name"):
            print(f"✅ Pushed to remote branch: {prometheus_result['remote_branch_name']}")

        if prometheus_result.get("issue_response"):
            print("📝 Prometheus analysis result generated")

    else:
        print(f"❌ Processing failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
