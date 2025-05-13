#!/usr/bin/env python3

import os
import sys
from typing import Dict, List, Optional
from dotenv import load_dotenv
from github import Github
from github.GithubException import GithubException
import re
import requests

class OwnersAnalyzer:
    def __init__(self, token: str, org: str, repo: str):
        self.github = Github(token)
        self.org = org
        self.repo = repo
        self.repository = self.github.get_repo(f"{org}/{repo}")

    def get_owners_files(self) -> List[Dict]:
        """Find all OWNERS files in the repository."""
        owners_files = []
        
        try:
            # Get the default branch
            default_branch = self.repository.default_branch
            print(f"Default branch: {default_branch}")
            
            # Get all files in the repository
            contents = self.repository.get_contents("", ref=default_branch)
            
            # Recursively find all OWNERS files
            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    contents.extend(self.repository.get_contents(file_content.path, ref=default_branch))
                elif file_content.name == "OWNERS":
                    owners_files.append({"path": file_content.path})
            
            print(f"Found {len(owners_files)} OWNERS files")
            return owners_files
            
        except GithubException as e:
            print(f"Error accessing repository: {e}")
            return []

    def get_file_content(self, path: str) -> Optional[str]:
        """Get the content of a file from the repository."""
        try:
            content = self.repository.get_contents(path)
            return content.decoded_content.decode("utf-8")
        except GithubException as e:
            print(f"Error getting file content for {path}: {e}")
            return None

    def analyze_owners_files(self) -> Dict[str, Dict[str, List[str]]]:
        """Analyze all OWNERS files and return a mapping of paths to labels and owners."""
        owners_files = self.get_owners_files()
        results = {}
        
        print("\nProcessing OWNERS files:")
        for file_info in owners_files:
            path = file_info["path"]
            print(f"\nProcessing path: {path}")
            # Remove "/OWNERS" from the path
            clean_path = path.replace("/OWNERS", "")
            print(f"Cleaned path: {clean_path}")
            content = self.get_file_content(file_info["path"])  # Use original path for content retrieval
            
            if content:
                print(f"Content found, length: {len(content)}")
                # Parse OWNERS file content
                labels = []
                owners = []
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        print(f"Processing line: {line}")
                        # Parse jira-project values
                        if line.startswith("jira-project"):
                            # Extract value between quotes (single or double)
                            match = re.search(r'jira-project\s+[\'"]?([^\'"]+)[\'"]?', line)
                            if match:
                                labels.append("jira-project")
                                owners.append(match.group(1))
                                print(f"Found jira-project: {match.group(1)}")
                        # Parse jira-component values
                        elif line.startswith("jira-component"):
                            # Extract value between quotes (single or double)
                            match = re.search(r'jira-component\s+[\'"]?([^\'"]+)[\'"]?', line)
                            if match:
                                labels.append("jira-component")
                                owners.append(match.group(1))
                                print(f"Found jira-component: {match.group(1)}")
                
                if labels and owners:  # Only add paths that have valid parsed owners
                    print(f"Adding {len(labels)} labels and owners to results for path: {clean_path}")
                    results[clean_path] = {
                        "labels": labels,
                        "owners": owners
                    }
                else:
                    print(f"No valid owners found for path: {clean_path}")
            else:
                print(f"No content found for path: {path}")
        
        print(f"\nFinal results count: {len(results)} paths")
        return results

def main():
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Get GitHub token and Endor token from environment variables
    github_token = os.getenv('GITHUB_TOKEN')
    endor_token = os.getenv('ENDOR_TOKEN')
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        sys.exit(1)
    if not endor_token:
        print("Error: ENDOR_TOKEN environment variable not set")
        sys.exit(1)

    # Get organization, repository, project UUID, and namespace from command line arguments
    if len(sys.argv) != 5:
        print("Usage: python owners_analyzer.py <organization> <repository> <endor-project-uuid> <endor-namespace>")
        sys.exit(1)

    org = sys.argv[1]
    repo = sys.argv[2]
    project_uuid = sys.argv[3]
    endor_namespace = sys.argv[4]
    
    print(f"Attempting to access repository: {org}/{repo}")
    print(f"Token length: {len(github_token)} characters")
    print(f"Token first 4 chars: {github_token[:4]}...")

    try:
        # Initialize GitHub client and verify repository access
        github = Github(github_token)
        
        # Print the base URL being used
        print(f"\nGitHub API Base URL: {github._Github__requester.base_url}")
        
        # Try to get the repository directly
        try:
            print(f"\nTrying to access repository: {org}/{repo}")
            repository = github.get_repo(f"{org}/{repo}")
            print(f"Repository '{org}/{repo}' found. Starting OWNERS file search...")
        except GithubException as e:
            print(f"Error accessing repository: {e}")
            print(f"Request URL: {e.url if hasattr(e, 'url') else 'Unknown'}")
            print(f"Status code: {e.status}")
            print(f"Data: {e.data}")
            print("\nPossible issues:")
            print("1. Repository name might be incorrect")
            print("2. Repository might be private and token doesn't have access")
            print("3. Organization name might be incorrect")
            print("4. Token might not have the 'repo' scope")
            sys.exit(1)

        analyzer = OwnersAnalyzer(github_token, org, repo)
        results = analyzer.analyze_owners_files()
        
        # Print results as Python dictionary before submitting
        print(f"\nOWNERS files found in {org}/{repo}:")
        print("-" * 50)
        print(results)
        
        # Prepare payload for EndorLabs API
        payload = {
            "meta": {
                "description": f"Code owner data for {repo}",
                "name": repo,
                "parent_kind": "Project",
                "parent_uuid": project_uuid
            },
            "spec": {
                "patterns": results
            },
            "tenant_meta": {
                "namespace": endor_namespace
            }
        }
        url = f"https://api.endorlabs.com/v1/namespaces/{endor_namespace}/codeowners"
        headers = {
            "Request-Timeout": "60",
            "Authorization": f"Bearer {endor_token}"
        }
        print(f"\nPosting code owner data to: {url}")
        response = requests.post(url, json=payload, headers=headers)
        print(f"Response body: {response.text}")
        print(f"Response status: {response.status_code}")

    except GithubException as e:
        print(f"Unexpected error: {e}")
        print(f"Request URL: {e.url if hasattr(e, 'url') else 'Unknown'}")
        print(f"Status code: {e.status}")
        print(f"Data: {e.data}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 