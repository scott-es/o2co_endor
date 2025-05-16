# OWNERS File Analyzer

This script analyzes OWNERS files in a GitHub repository and syncs the ownership data to Endor Labs.

## Features

- Automatically detects GitHub organization and repository from git remote
- Finds all OWNERS files in the repository using git commands
- Parses jira-project and jira-component entries
- Supports both single and double quotes in OWNERS files
- Syncs ownership data to Endor Labs API
- Debug mode for detailed output
- Dry run mode to preview changes without making API calls

## Prerequisites

- Python 3.6+
- Poetry for dependency management
- Git repository with remote origin configured
- Endor Labs token

## Installation

1. Clone the repository
2. Install dependencies:

```bash
poetry install
```

## Configuration

Create a `.env` file in the project root with your Endor token:

```env
ENDOR_TOKEN=your_endor_token
```

## Usage

The script must be run from within a git repository. It will automatically detect the GitHub organization and repository from the git remote.

Basic usage:

```bash
poetry run python o2co_endor/main.py <endor-namespace>
```

### Arguments

- `endor-namespace`: Endor namespace

### Flags

- `--debug`: Enable debug output (shows detailed processing information)
- `--no-dry-run`: Make the HTTP POST request to Endor Labs (default is dry run)

### Examples

1. Dry run with debug output:

```bash
poetry run python o2co_endor/main.py my-namespace --debug
```

2. Actually sync to Endor Labs:

```bash
poetry run python o2co_endor/main.py my-namespace --no-dry-run
```

3. Debug mode with actual sync:

```bash
poetry run python o2co_endor/main.py my-namespace --debug --no-dry-run
```

## Output

The script will:
1. Detect the GitHub organization and repository from git remote
2. Find and parse all OWNERS files in the repository
3. Display the number of OWNERS files found
4. Show the ownership entries found for each path
5. In dry run mode (default):
   - Show the URL that would be used
   - Display the payload that would be sent
6. In non-dry-run mode:
   - Make the HTTP POST request to Endor Labs
   - Show the response status and body
   - Exit with code 1 if the request fails

## Error Handling

The script will exit with code 1 if:
- Not run from within a git repository
- Git remote origin is not configured
- Required environment variables are missing
- HTTP POST request returns a non-200 status code
- Any unexpected errors occur

## License

MIT
