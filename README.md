# Airfold Apps E2E

An AI-powered web application builder that uses Claude to automatically generate full-stack Next.js applications with database integration, version control, and live preview.

## Overview

This project provides a complete end-to-end solution for building web applications using AI agents:

- **Frontend**: React/TypeScript interface for managing projects and features
- **Backend**: FastAPI server orchestrating Claude AI agent execution
- **Database**: Neon PostgreSQL with branch-based development workflow
- **Version Control**: Automated GitHub repository management
- **Agent**: Claude Code SDK for building complete Next.js applications

## Architecture

```
                     HTTP
+---------------+  --------->  +---------------+
|   Frontend    |              |    FastAPI    |
|   (React)     |  <---------  |    Server     |
+---------------+              +---------------+
                                       |
                   +-------------------+-------------------+
                   |                   |                   |
                   v                   v                   v
           +---------------+   +---------------+   +---------------+
           | Claude Agent  |   |    GitHub     |   |     Neon      |
           |      SDK      |   |      API      |   |  PostgreSQL   |
           +---------------+   +---------------+   +---------------+
                   |
                   v
           +---------------+
           |   Next.js     |
           |     Apps      |
           |   (tmp/)      |
           +---------------+
```

## Prerequisites

- **Python**: 3.13+ (managed with `uv`)
- **Node.js**: 18+ (for frontend and generated apps)
- **npm**: 10+
- **Git**: For repository management
- **Anthropic API Key**: For Claude AI agent
- **GitHub Personal Access Token**: For repository operations
- **Neon Account**: For PostgreSQL database branching

## Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd airfold-apps-e2e
```

### 2. Install Python Dependencies

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync
```

### 3. Set Up Environment Variables

Create or edit `env_vars/.env` with the following:

```bash
# Required API Keys
ANTHROPIC_API_KEY=sk-ant-api03-...
GITHUB_TOKEN=ghp_...
NEON_API_KEY=napi_...

# Optional (for other LLM providers)
GOOGLE_VERTEX_API=...
AWS_BEARER_TOKEN_BEDROCK=...
```

**How to get API keys:**
- **Anthropic API Key**: https://console.anthropic.com/
- **GitHub Token**: Settings → Developer settings → Personal access tokens → Generate new token (classic)
  - Required scopes: `repo`, `workflow`
- **Neon API Key**: https://console.neon.tech/ → Account Settings → API Keys

### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
```

## Running the Project

### Start Backend Server

```bash
# From project root
uv run python main.py
```

The backend will start on **http://localhost:8080**

### Start Frontend Development Server

```bash
# In a new terminal
cd frontend
npm run dev
```

The frontend will start on **http://localhost:5173**

### Access the Application

Open your browser to **http://localhost:5173**

## How It Works

### 1. Project Creation

1. Enter your GitHub username
2. Create a new project with a name (e.g., "expenses-app")
3. The system creates a GitHub repository from the `init_git` template

### 2. Feature Development

1. Click "Add Feature" in the project view
2. Enter a feature name and detailed prompt
3. The system:
   - Creates a Neon database branch
   - Clones the GitHub repository to `tmp/`
   - Writes database credentials to `.env`
   - Runs Claude AI agent with your prompt
   - Agent builds the complete feature (schema, API, UI)
   - Commits and pushes changes to GitHub
   - Promotes Neon branch to default
   - Starts Next.js dev server

### 3. Live Preview

- View your application at **http://localhost:3000** (in the iframe)
- Changes are immediately visible
- Each feature builds on previous features

## Project Structure

```
airfold-apps-e2e/
├── main.py                 # FastAPI server & orchestration
├── cc_vibecode/            # Core modules
│   ├── git.py              # GitHub API integration
│   ├── neon.py             # Neon database branching
│   ├── server.py           # Next.js dev server management
│   └── logger.py           # Logging configuration
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API client
│   │   └── types/          # TypeScript types
│   └── package.json
├── init_git/               # Next.js template repository
│   ├── app/                # Next.js app directory
│   ├── components/         # React components
│   ├── lib/                # Utilities
│   ├── prisma/             # Prisma schema
│   └── package.json
├── prompts.yaml            # System prompts for Claude agent
├── env_vars/.env           # API keys and credentials
└── tmp/                    # Working directory for generated apps
```

## Key Features

### Automated GitHub Repository Management

- Creates repositories from template automatically
- Handles repository initialization and cloning
- Manages git operations (commit, push, rebase)
- 5-second delay to handle GitHub's async template copying

### Neon Database Branching

- Creates isolated database branches per project
- Grants proper permissions for schema modifications
- Supports Prisma migrations for version-controlled schemas
- Promotes branches to default after feature completion
- Automatic cleanup of temporary roles and endpoints

### Claude AI Agent Integration

- Uses Claude Code SDK for autonomous development
- Follows strict Next.js + TypeScript + Prisma patterns
- Implements complete features from natural language prompts
- Handles migrations, API routes, UI components, and testing
- 10-minute timeout for long-running builds

### Next.js App Generation

- **Stack**: Next.js 14+, TypeScript, Tailwind CSS, Prisma, shadcn/ui
- **Features**: Database models, API routes, UI components, validation
- **Migrations**: Version-controlled Prisma migrations
- **Development Server**: Auto-starts on port 3000 with logging

## Environment Variables

### Backend (`env_vars/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude AI API key |
| `GITHUB_TOKEN` | Yes | GitHub personal access token |
| `NEON_API_KEY` | Yes | Neon database API key |

### Generated Apps (`tmp/.env`)

Automatically created for each project:

```bash
DATABASE=neondb
USER=<role-name>
PASSWORD=<generated-password>
HOST=<neon-endpoint>.aws.neon.tech
DATABASE_URL=postgresql://<user>:<password>@<host>/<database>
```

## Troubleshooting

### Frontend Shows "Failed" but Feature Works

**Issue**: Long-running agent executions (5-10 minutes) may timeout on the frontend, but the backend continues and completes successfully.

**Solution**: Check:
- Backend logs in `logs/app-*.log`
- Git commits: `git log --oneline` in `tmp/`
- Running server: `ps aux | grep "next dev"`
- http://localhost:3000 still works

The 10-minute timeout in `frontend/src/services/api.ts` should prevent this.

### Server Won't Start

**Issue**: "Permission denied" or "address already in use"

**Solution**:
```bash
# Kill existing servers
pkill -f "next dev"
pkill -f "npm run dev"

# Remove PID file
rm tmp/.dev-server.pid

# Try again
```

### Database Migration Errors

**Issue**: "permission denied for schema public"

**Solution**: This was fixed in `cc_vibecode/neon.py` by quoting role names in SQL grants. If you still see this, check that role names with hyphens are properly quoted.

### Template Repository Empty After Clone

**Issue**: Cloned repository has no files

**Solution**: The 5-second delay in `cc_vibecode/git.py:139` should fix this. If it persists, increase the delay or manually verify the template at https://github.com/shnkreddy98/init_git

## Development

### Running Tests

```bash
# Backend tests (if available)
uv run pytest

# Frontend tests
cd frontend
npm test
```

### Viewing Logs

```bash
# Backend logs
tail -f logs/app-*.log

# Next.js dev server logs
tail -f tmp/.dev-server.log
```

### Modifying System Prompts

Edit `prompts.yaml` to customize how Claude builds applications:
- `first_prompt`: Instructions for initial project setup
- `therest_prompt`: Instructions for subsequent features

## Tech Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: CSS Modules
- **HTTP Client**: Axios (10-min timeout for agent calls)
- **State**: React hooks + localStorage

### Backend
- **Framework**: FastAPI
- **AI Agent**: Claude Code SDK (Sonnet 4.5)
- **Database Client**: Neon API + psycopg2
- **Git Client**: PyGithub
- **Server**: Uvicorn (production ASGI)

### Generated Apps
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui
- **Database**: PostgreSQL via Prisma ORM
- **Validation**: Zod schemas

## API Endpoints

### Backend API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/execute` | Execute Claude agent to build a feature |

Request body:
```json
{
  "url": "git@github.com:username/repo.git",
  "projectName": "my-app",
  "branchName": "feature-name",
  "dirPath": "tmp",
  "prompt": "Build an expense tracker...",
  "first": true
}
```

Response:
```json
{
  "success": true,
  "message": "Feature completed...",
  "previewUrl": "http://localhost:3000"
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT

## Support

For issues or questions:
- Check the logs in `logs/` directory
- Review error messages in terminal output
- Verify all API keys are set correctly in `env_vars/.env`
- Ensure GitHub template repository exists: https://github.com/shnkreddy98/init_git
