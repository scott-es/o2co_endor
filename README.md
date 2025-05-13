# OWNERS 2 CODEOWNERS Endor

The script will output a list of all OWNERS files found in the repository, along with the owners listed in each file, and then update an Endor Labs project with the data.

## Prerequisites

- Python 3.7+
- Poetry (Python package manager)

## Installation

1. Clone this repository
2. Install dependencies:

```bash
poetry install
```

## Configuration

Create a `.env` file in the project root with your GitHub token and Endor token:

```env
GITHUB_TOKEN=your_github_token_here
ENDOR_TOKEN=your_endor_token_here
```

You can create a GitHub token at: <https://github.com/settings/tokens>

## Usage

Run the script using Poetry:

```bash
poetry run python o2co_endor/main.py <organization> <repository> <endor-project-uuid> <endor-namespace>
```

For example:

```bash
poetry run python o2co_endor/main.py kubernetes kubernetes project-uuid-123 endor-namespace
```

## Features

- Searches for all OWNERS files in a repository
- Parses OWNERS file contents
- Handles GitHub API pagination
- Respects GitHub API rate limits
- Supports environment variable configuration
- Updates CodeOwners data in Endor Labs for specified project

## License

MIT
