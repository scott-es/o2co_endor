#!/usr/bin/env python3

import os
import sys
import re
import requests
import argparse
import subprocess
from typing import Dict, List, Optional
from dotenv import load_dotenv

class OwnersAnalyzer:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.org, self.repo = self._get_git_info()

    def debug_print(self, message: str):
        """Print message only if debug mode is enabled."""
        if self.debug:
            print(message)

    def _get_git_info(self) -> tuple[str, str]:
        """Get GitHub organization and repository name from git remote."""
        try:
            # Get the remote URL
            remote_url = subprocess.check_output(
                ['git', 'config', '--get', 'remote.origin.url'],
                stderr=subprocess.STDOUT
            ).decode('utf-8').strip()
            
            # Parse the URL to get org and repo
            # Handle both HTTPS and SSH URLs
            if remote_url.startswith('https://'):
                # https://github.com/org/repo.git
                parts = remote_url.rstrip('.git').split('/')
                org = parts[-2]
                repo = parts[-1]
            else:
                # git@github.com:org/repo.git
                parts = remote_url.rstrip('.git').split(':')[-1].split('/')
                org = parts[0]
                repo = parts[1]
            
            print(f"Found GitHub repository: {org}/{repo}")
            return org, repo
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting git remote info: {e}")
            sys.exit(1)

    def get_owners_files(self) -> List[Dict]:
        """Find all OWNERS files in the repository using git ls-files."""
        owners_files = []
        
        try:
            # Use git ls-files to find all OWNERS files
            print("\nSearching for OWNERS files... ", end="")
            output = subprocess.check_output(
                ['git', 'ls-files', '**/OWNERS'],
                stderr=subprocess.STDOUT
            ).decode('utf-8').strip()
            
            # Process the output
            if output:
                for path in output.split('\n'):
                    if path:  # Skip empty lines
                        owners_files.append({"path": path})
            
            self.debug_print(f"No. of OWNERS files found: {len(owners_files)}")
            return owners_files
            
        except subprocess.CalledProcessError as e:
            print(f"Error searching for OWNERS files: {e}")
            return []

    def get_file_content(self, path: str) -> Optional[str]:
        """Get the content of a file from the repository."""
        try:
            with open(path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {path}: {e}")
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

def sync_to_endor(results: Dict[str, Dict[str, List[str]]], gh_org: str, repository: str, namespace: str, endor_token: str) -> None:
    """Sync ownership data to Endor Labs API.
    
    Args:
        results: Dictionary of path to labels and owners
        repository: Repository name
        project_uuid: Endor project UUID
        namespace: Endor namespace
        endor_token: Endor API token
        dry_run: If True, only show what would be sent without making the request
    """
    # Get project UUID
    project_uuid = ""
    try:
        response = get_endor_project_uuid_from_name(gh_org, repository, namespace, endor_token)
        if response.status_code != 200:
                print(f"\nError: HTTP request failed with status code {response.status_code}")
                sys.exit(1)
        else:
            project_uuid = response.json()['list']['objects'][0]['uuid']
            print(f"Found project with UUID: {project_uuid}", end="")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
    
    # print(f"\n Found project in Endor Labs with UUID: {project_uuid}")
    # Prepare payload for EndorLabs API
    payload = {
        "meta": {
            "description": f"Code owner data for {gh_org}/{repository}",
            "name": repository,
            "parent_kind": "Project",
            "parent_uuid": project_uuid
        },
        "spec": {
            "patterns": results
        },
        "tenant_meta": {
            "namespace": namespace
        }
    }
    url = f"https://api.endorlabs.com/v1/namespaces/{namespace}/codeowners"
    headers = {
        "Request-Timeout": "60",
        "Authorization": f"Bearer {endor_token}"
    }
        
    response = requests.post(url, json=payload, headers=headers)
        
    return response

def get_endor_project_uuid_from_name(gh_org: str, gh_repo: str, namespace: str, endor_token: str) -> str:
    """Get Endor project uuid from its name."""

    project_name = f"https://github.com/{gh_org}/{gh_repo}.git"

    params = {
        "list_parameters.filter": f"meta.name=='{project_name}'"
    }

    # print(f"{params=}")

    url = f"https://api.endorlabs.com/v1/namespaces/{namespace}/projects"
    headers = {
        "Request-Timeout": "60",
        "Authorization": f"Bearer {endor_token}"
    }
        
    response = requests.get(url, params=params, headers=headers)
    # print(f"{response.url=}")
        
    return response

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Analyze OWNERS files in a GitHub repository')
    parser.add_argument('endor_namespace', help='Endor namespace')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--no-dry-run', action='store_true', help='Make the HTTP POST request (default is dry run)')
    args = parser.parse_args()

    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Get Endor token from environment variables
    endor_token = os.getenv('ENDOR_TOKEN')
    if not endor_token:
        print("Error: ENDOR_TOKEN environment variable not set")
        sys.exit(1)

    try:
        analyzer = OwnersAnalyzer(args.debug)
        results = analyzer.analyze_owners_files()
        
        # Print results as Python dictionary before submitting
        # print(f"\nOWNERS files found in {analyzer.org}/{analyzer.repo}:")
        # print("-" * 50)
        # print(results)
        
        # Sync to Endor Labs
        if not args.no_dry_run:
            print("\nDRY RUN MODE - Skipping syncing with Endor Labs")
        else:
            print(f"\nSyncing to Endor Labs as CodeOwners... ", end="")
            response = sync_to_endor(
                results=results,
                gh_org=analyzer.org,
                repository=analyzer.repo,
                namespace=args.endor_namespace,
                endor_token=endor_token
            )

            if response.status_code != 200:
                print(f"\nError: HTTP request failed with status code {response.status_code}")
                sys.exit(1)
            else:
                print("\n\nDone\n")

    except Exception as e:
        print(f"Unexpected error: {e}")
        raise(e)
        sys.exit(1)

if __name__ == "__main__":
    main() 