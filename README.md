# OWNERS File Analyzer

This script analyzes OWNERS files in a GitHub repository and syncs the ownership data to Endor Labs.

## Features

- Finds all OWNERS files in a GitHub repository
- Parses jira-project and jira-component entries
- Supports both single and double quotes in OWNERS files
- Syncs ownership data to Endor Labs API
- Debug mode for detailed output
- Dry run mode to preview changes without making API calls

## Prerequisites

- Python 3.6+
- Poetry for dependency management
- GitHub token with repo access
- Endor Labs token

## Installation

1. Clone the repository
2. Install dependencies:

```bash
poetry install
```

## Configuration

Create a `.env` file in the project root with your tokens:

```env
GITHUB_TOKEN=your_github_token
ENDOR_TOKEN=your_endor_token
```

You can create a GitHub token at: <https://github.com/settings/tokens>

## Usage

Basic usage:

```bash
poetry run python o2co_endor/main.py <organization> <repository> <endor-project-uuid> <endor-namespace>
```

### Arguments

- `organization`: GitHub organization name
- `repository`: GitHub repository name
- `endor-project-uuid`: Endor project UUID
- `endor-namespace`: Endor namespace

### Flags

- `--debug`: Enable debug output (shows detailed processing information)
- `--no-dry-run`: Make the HTTP POST request to Endor Labs (default is dry run)

### Examples

1. Dry run with debug output:

```bash
poetry run python o2co_endor/main.py myorg myrepo project-uuid namespace --debug
```

2. Actually sync to Endor Labs:

```bash
poetry run python o2co_endor/main.py myorg myrepo project-uuid namespace --no-dry-run
```

3. Debug mode with actual sync:

```bash
poetry run python o2co_endor/main.py myorg myrepo project-uuid namespace --debug --no-dry-run
```

## Output

The script will:
1. Find and parse all OWNERS files in the repository
2. Display the number of OWNERS files found
3. Show the ownership entries found for each path
4. In dry run mode (default):
   - Show the URL that would be used
   - Display the payload that would be sent
5. In non-dry-run mode:
   - Make the HTTP POST request to Endor Labs
   - Show the response status and body
   - Exit with code 1 if the request fails

## Error Handling

The script will exit with code 1 if:
- Required environment variables are missing
- GitHub repository access fails
- HTTP POST request returns a non-200 status code
- Any unexpected errors occur

## License

MIT
