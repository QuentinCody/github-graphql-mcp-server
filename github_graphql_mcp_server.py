import os
import sys
import httpx
import json
import logging
from typing import Any, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    stream=sys.stderr)

# Helper function to print to stderr
# def log(message):
#    print(message, file=sys.stderr)

# GitHub Configuration - get directly from environment variables
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Simplify error handling and do more logging
if not GITHUB_TOKEN:
    logging.error("GitHub token not found in environment variables")
    logging.warning(f"Available environment variables: {list(os.environ.keys())}")
else:
    logging.info(f"Successfully loaded GitHub token starting with: {GITHUB_TOKEN[:4]}")

# GitHub GraphQL API Endpoint
GITHUB_GRAPHQL_API_URL = "https://api.github.com/graphql"

from mcp.server.fastmcp import FastMCP
mcp = FastMCP("github-graphql", version="0.1.0")
logging.info("GitHub GraphQL MCP Server initialized.")

async def make_github_request(query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Makes an authenticated GraphQL request to the GitHub API.
    Handles authentication and error checking.
    """
    if not GITHUB_TOKEN:
        logging.error("GitHub API token is missing. Cannot make request.")
        return {"errors": [{"message": "Server missing GitHub API token."}]}

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "MCPGitHubServer/0.1.0"
    }

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    async with httpx.AsyncClient() as client:
        try:
            logging.debug(f"Sending request to GitHub: {query[:100]}...")
            response = await client.post(
                GITHUB_GRAPHQL_API_URL,
                headers=headers,
                json=payload,
                timeout=30.0
            )

            # Log Rate Limit Info
            rate_limit = response.headers.get('X-RateLimit-Limit')
            rate_remaining = response.headers.get('X-RateLimit-Remaining')
            rate_reset = response.headers.get('X-RateLimit-Reset')
            if rate_limit is not None and rate_remaining is not None:
                 logging.info(f"GitHub Rate Limit: {rate_remaining}/{rate_limit} remaining. Resets at timestamp {rate_reset}.")
                 if int(rate_remaining) < 50:
                     logging.warning(f"GitHub Rate Limit low: {rate_remaining} remaining.")

            response.raise_for_status()
            logging.debug(f"GitHub response status: {response.status_code}")
            result = response.json()
            # Check for GraphQL errors within the response body
            if "errors" in result:
                logging.warning(f"GraphQL Errors: {result['errors']}")
            return result
        except httpx.RequestError as e:
            logging.error(f"HTTP Request Error: {e}", exc_info=True)
            return {"errors": [{"message": f"HTTP Request Error connecting to GitHub: {e}"}]}
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP Status Error: {e.response.status_code} - Response: {e.response.text[:500]}", exc_info=True)
            error_detail = f"HTTP Status Error: {e.response.status_code}"
            try:
                # Try to parse GitHub's error response if JSON
                err_resp = e.response.json()
                if "errors" in err_resp:
                    error_detail += f" - {err_resp['errors'][0]['message']}"
                elif "message" in err_resp:
                    error_detail += f" - {err_resp['message']}"
                else:
                    pass
            except json.JSONDecodeError:
                 pass

            return {"errors": [{"message": error_detail}]}
        except Exception as e:
            logging.error(f"Generic Error during GitHub request: {e}", exc_info=True)
            return {"errors": [{"message": f"An unexpected error occurred: {e}"}]}

@mcp.tool()
async def github_execute_graphql(query: str, variables: Dict[str, Any] = None) -> str:
    """
    Executes an arbitrary GraphQL query or mutation against the GitHub API.
    This powerful tool provides unlimited flexibility for any GitHub GraphQL operation
    by directly passing queries with full control over selection sets and variables.
    
    ## GraphQL Introspection
    You can discover the GitHub API schema using GraphQL introspection queries such as:
    
    ```graphql
    # Get all available query types
    query IntrospectionQuery {
      __schema {
        queryType { name }
        types {
          name
          kind
          description
          fields {
            name
            description
            args {
              name
              description
              type { name kind }
            }
            type { name kind }
          }
        }
      }
    }
    
    # Get details for a specific type
    query TypeQuery {
      __type(name: "Repository") {
        name
        description
        fields {
          name
          description
          type { name kind ofType { name kind } }
        }
      }
    }
    ```
    
    ## Common Operation Patterns
    
    ### Fetching a repository
    ```graphql
    query GetRepository($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        name
        description
        url
        stargazerCount
        forkCount
        issues(first: 10, states: OPEN) {
          nodes {
            title
            url
            createdAt
          }
        }
      }
    }
    ```
    Variables: `{"owner": "octocat", "name": "Hello-World"}`
    
    ### Fetching user information
    ```graphql
    query GetUser($login: String!) {
      user(login: $login) {
        name
        bio
        avatarUrl
        url
        repositories(first: 10, orderBy: {field: STARGAZERS, direction: DESC}) {
          nodes {
            name
            description
            stargazerCount
          }
        }
      }
    }
    ```
    Variables: `{"login": "octocat"}`
    
    ### Creating an issue
    ```graphql
    mutation CreateIssue($repositoryId: ID!, $title: String!, $body: String) {
      createIssue(input: {
        repositoryId: $repositoryId,
        title: $title,
        body: $body
      }) {
        issue {
          id
          url
          number
        }
      }
    }
    ```
    
    ### Searching repositories
    ```graphql
    query SearchRepositories($query: String!, $first: Int!) {
      search(query: $query, type: REPOSITORY, first: $first) {
        repositoryCount
        edges {
          node {
            ... on Repository {
              name
              owner {
                login
              }
              description
              url
              stargazerCount
            }
          }
        }
      }
    }
    ```
    Variables: `{"query": "language:javascript stars:>1000", "first": 10}`
    
    ## Pagination
    For paginated results, use the `after` parameter with the `endCursor` from previous queries:
    ```graphql
    query GetNextPage($login: String!, $after: String) {
      user(login: $login) {
        repositories(first: 10, after: $after) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            name
          }
        }
      }
    }
    ```
    
    ## Error Handling Tips
    - Check for the "errors" array in the response
    - Common error reasons:
      - Invalid GraphQL syntax: verify query structure
      - Unknown fields: check field names through introspection
      - Missing required fields: ensure all required fields are in queries
      - Permission issues: verify API token has appropriate permissions
      - Rate limits: GitHub has API rate limits which may be exceeded
    
    ## Variables Usage
    Variables should be provided as a Python dictionary where:
    - Keys match the variable names defined in the query/mutation
    - Values follow the appropriate data types expected by GitHub
    - Nested objects must be structured according to GraphQL input types
    
    Args:
        query: The complete GraphQL query or mutation to execute.
        variables: Optional dictionary of variables for the query. Should match
                  the parameter names defined in the query with appropriate types.

    Returns:
        JSON string containing the complete response from GitHub, including data and errors if any.
    """
    if not query:
        logging.warning("Received empty query for github_execute_graphql.")
        return json.dumps({"errors": [{"message": "Query cannot be empty."}]})

    logging.info(f"Executing github_execute_graphql with query starting: {query[:50]}...")

    # Make the API call
    result = await make_github_request(query, variables)

    # Return the raw result as JSON
    return json.dumps(result)

if __name__ == "__main__":
    logging.info("Attempting to run GitHub GraphQL MCP server via stdio...")
    # Basic check before running
    if not GITHUB_TOKEN:
        logging.critical("FATAL: Cannot start server, GitHub token missing.")
        sys.exit(1)
    else:
        logging.info(f"Configured for GitHub GraphQL API with token: {GITHUB_TOKEN[:4]}...")
        try:
            mcp.run(transport='stdio')
            logging.info("Server stopped.")
        except Exception as e:
            logging.exception("Error running server")
            sys.exit(1)