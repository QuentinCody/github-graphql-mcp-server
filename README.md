# GitHub GraphQL MCP Server

A Model Context Protocol (MCP) server that provides access to GitHub's GraphQL API. This server exposes a single tool that allows executing arbitrary GraphQL queries and mutations against GitHub's API.

## Features

- Execute any GraphQL query against GitHub's API
- Comprehensive error handling and reporting
- Detailed documentation with example queries
- Support for variables in GraphQL operations

## Prerequisites

- Python 3.10 or higher
- A GitHub Personal Access Token (PAT)

## Installation

1. Clone this repository
2. Set up a virtual environment (recommended):
   ```bash
   # On macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   
   # On Windows
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Server

```bash
# If using a virtual environment, make sure it's activated
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run the server with your GitHub token
GITHUB_TOKEN=your_github_token_here python github_graphql_mcp_server.py
```

### Configuring with Claude for Desktop

Add the following to your Claude Desktop configuration file:

```json
{
  "github-graphql": {
    "command": "/absolute/path/to/your/.venv/bin/python",
    "args": [
        "/absolute/path/to/github_graphql_mcp_server.py"
    ],
    "options": {
        "cwd": "/absolute/path/to/repository"
    },
    "env": {
        "GITHUB_TOKEN": "your_github_token_here"
    }
  }
}
```

Replace `/absolute/path/to/` with the actual path to your server file and add your GitHub token.

### Example Queries

#### Get Repository Information

```graphql
query GetRepo($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    name
    description
    stargazerCount
    url
    createdAt
    owner {
      login
      avatarUrl
    }
  }
}
```

Variables:
```json
{
  "owner": "octocat",
  "name": "Hello-World"
}
```

#### Search Repositories

```graphql
query SearchRepos($query: String!, $first: Int!) {
  search(query: $query, type: REPOSITORY, first: $first) {
    repositoryCount
    edges {
      node {
        ... on Repository {
          name
          owner { login }
          description
          stargazerCount
          url
        }
      }
    }
  }
}
```

Variables:
```json
{
  "query": "language:python stars:1000",
  "first": 5
}
```

#### Get User Information

```graphql
query GetUserInfo($login: String!) {
  user(login: $login) {
    name
    login
    bio
    avatarUrl
    followers {
      totalCount
    }
    repositories(first: 5, orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes {
        name
        description
        stargazerCount
      }
    }
  }
}
```

Variables:
```json
{
  "login": "octocat"
}
```

## GitHub API Rate Limits

Be aware of GitHub's API rate limits:
- Authenticated requests: 5,000 requests per hour
- Unauthenticated requests: 60 requests per hour

## Troubleshooting

If you encounter issues:

1. Check your GitHub token has the correct permissions
2. Verify your virtual environment is properly set up and activated
3. Ensure your token is correctly set in the environment variables
4. If using Claude Desktop, ensure the path to Python is correct (use absolute path to the virtual environment Python)
5. Look at the server logs for error messages
6. Ensure your GraphQL query is valid for GitHub's schema
7. Restart Claude for Desktop after making config changes

### Common Errors

**`spawn python ENOENT`**
- This error means the Python executable wasn't found
- Solution: Use the full path to your Python executable in the virtual environment (e.g., `/path/to/your/.venv/bin/python`)

**`ModuleNotFoundError: No module named 'httpx'` (or other packages)**
- The Python environment doesn't have the required dependencies installed
- Solution: Make sure you've activated the virtual environment and run `pip install -r requirements.txt`

**`Error: GitHub token not found in environment variables`**
- The server couldn't find your GitHub token
- Solution: Make sure you've set the GITHUB_TOKEN environment variable