#!/usr/bin/env python3

import os
import sys
import re
import requests
import argparse
from typing import Dict, List, Optional
from dotenv import load_dotenv
from github import Github
from github.GithubException import GithubException

class OwnersAnalyzer:
    def __init__(self, token: str, org: str, repo: str, debug: bool = False):
        self.github = Github(token)
        self.org = org
        self.repo = repo
        self.repository = self.github.get_repo(f"{org}/{repo}")
        self.debug = debug

    def debug_print(self, message: str):
        """Print message only if debug mode is enabled."""
        if self.debug:
            print(message)

    def get_owners_files(self) -> List[Dict]:
        """Find all OWNERS files in the repository."""
        owners_files = []
        
        try:
            # Get the default branch
            default_branch = self.repository.default_branch
            print(f"Default branch: {default_branch}")
            
            # Get all files in the repository
            print("\nSearching for OWNERS files... ", end="")
            contents = self.repository.get_contents("", ref=default_branch)
            
            # Recursively find all OWNERS files
            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    contents.extend(self.repository.get_contents(file_content.path, ref=default_branch))
                elif file_content.name == "OWNERS":
                    owners_files.append({"path": file_content.path})
            
            self.debug_print(f"No. of OWNERS files found: {len(owners_files)}")
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
        
        print(f"found {len(owners_files)}")
        for file_info in owners_files:
            path = file_info["path"]
            self.debug_print(f"\nProcessing path: {path}")
            # Remove "/OWNERS" from the path
            clean_path = path.replace("/OWNERS", "")
            self.debug_print(f"Cleaned path: {clean_path}")
            content = self.get_file_content(file_info["path"])  # Use original path for content retrieval
            
            if content:
                self.debug_print(f"Content found, length: {len(content)}")
                # Parse OWNERS file content
                labels = []
                owners = []
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self.debug_print(f"Processing line: {line}")
                        # Parse jira-project values
                        if line.startswith("jira-project"):
                            # Extract value between quotes (single or double)
                            match = re.search(r'jira-project\s+[\'"]?([^\'"]+)[\'"]?', line)
                            if match:
                                labels.append("jira-project")
                                owners.append(match.group(1))
                                self.debug_print(f"Found jira-project: {match.group(1)}")
                        # Parse jira-component values
                        elif line.startswith("jira-component"):
                            # Extract value between quotes (single or double)
                            match = re.search(r'jira-component\s+[\'"]?([^\'"]+)[\'"]?', line)
                            if match:
                                labels.append("jira-component")
                                owners.append(match.group(1))
                                self.debug_print(f"Found jira-component: {match.group(1)}")
                
                if labels and owners:  # Only add paths that have valid parsed owners
                    print(f"-  Path '{clean_path}': {len(owners)} ownership entries found")
                    results[clean_path] = {
                        "labels": labels,
                        "owners": owners
                    }
                else:
                    print(f"No valid owners found for path: {clean_path}")
            else:
                print(f"No content found for path: {path}")
        
        return results

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Analyze OWNERS files in a GitHub repository')
    parser.add_argument('organization', help='GitHub organization name')
    parser.add_argument('repository', help='GitHub repository name')
    parser.add_argument('endor_project_uuid', help='Endor project UUID')
    parser.add_argument('endor_namespace', help='Endor namespace')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--no-dry-run', action='store_true', help='Make the HTTP POST request (default is dry run)')
    args = parser.parse_args()

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

    analyzer = OwnersAnalyzer(github_token, args.organization, args.repository, args.debug)

    try:
        # Initialize GitHub client and verify repository access
        github = Github(github_token)
        
        # Print the base URL being used
        print(f"\nGitHub API Base URL: {github._Github__requester.base_url}")
        
        # Try to get the repository directly
        try:
            repository = github.get_repo(f"{args.organization}/{args.repository}")
            print(f"Repository: '{args.organization}/{args.repository}'")
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

        results = analyzer.analyze_owners_files()
        
        # Print results as Python dictionary before submitting
        analyzer.debug_print(f"\nOWNERS files found in {args.organization}/{args.repository}:")
        analyzer.debug_print("-" * 50)
        analyzer.debug_print(results)
        
        # Prepare payload for EndorLabs API
        payload = {
            "meta": {
                "description": f"Code owner data for {args.repository}",
                "name": args.repository,
                "parent_kind": "Project",
                "parent_uuid": args.endor_project_uuid
            },
            "spec": {
                "patterns": results
            },
            "tenant_meta": {
                "namespace": args.endor_namespace
            }
        }
        url = f"https://api.endorlabs.com/v1/namespaces/{args.endor_namespace}/codeowners"
        headers = {
            "Request-Timeout": "60",
            "Authorization": f"Bearer {endor_token}"
        }

        if not args.no_dry_run:
            print("\nDRY RUN MODE - Skipping HTTP POST request")
            print(f"Would have posted to: {url}")
            print("Payload that would have been sent:")
            print("-" * 50)
            print(payload)
        else:
            print("\nSyncing to Endor Labs as CodeOwners... ", end="")
            response = requests.post(url, json=payload, headers=headers)
            analyzer.debug_print(f"Response body: {response.text}")
            analyzer.debug_print(f"Response status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error: HTTP request failed with status code {response.status_code}")
                sys.exit(1)
            else:
                print("Done")

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