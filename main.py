import asyncio
import os
import sys
import uvicorn
import yaml  # type: ignore

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
    query,
)
from textwrap import dedent
from cc_vibecode.git import CustomGitAPI
from cc_vibecode.neon import CustomNeonAPI, BranchInfo
from cc_vibecode.logger import create_logger
from cc_vibecode.server import add_scripts_to_package_json, start_server_background, stop_server
from fastapi import FastAPI
from pydantic import BaseModel

logger = create_logger("agent")

git = CustomGitAPI(os.getenv("GITHUB_TOKEN", ""))
neon = CustomNeonAPI(os.getenv("NEON_API_KEY", ""))
app = FastAPI()

class ExecuteRequest(BaseModel):
    url: str
    projectName: str
    branchName: str
    dirPath: str
    prompt: str
    first: bool

class ExecuteResponse(BaseModel):
    success: bool
    message: str | None = None
    previewUrl: str | None = None

def read(first: bool = False):
    with open("prompts.yaml", "r") as f:
        prompts = yaml.safe_load(f)

    if first:
        return prompts["first_prompt"]
    else:
        return prompts["therest_prompt"]


def write_connection_to_env(connection: BranchInfo, env_path: str = ".env"):
    # Construct the full DATABASE_URL from individual parameters
    database_url = f"postgresql://{connection.user}:{connection.password}@{connection.host}/{connection.database}"

    with open(env_path, "a+") as f:
        # Write individual parameters
        f.write(f"\nDATABASE={connection.database}\n")
        f.write(f"USER={connection.user}\n")
        f.write(f"PASSWORD={connection.password}\n")
        f.write(f"HOST={connection.host}\n")
        # Also write the constructed DATABASE_URL for Prisma
        f.write(f"DATABASE_URL={database_url}\n")


def pre_agent_run(
    url: str, proj_name: str, branch_name: str, dir_path: str
) -> BranchInfo | Exception:
    # init git and neon
    # if not exists create git and neon
    # Convert to absolute path for consistency
    abs_dir_path = os.path.abspath(dir_path)

    # Clean up existing directory from previous runs
    stop_server(abs_dir_path)
    if os.path.exists(abs_dir_path):
        import shutil
        shutil.rmtree(abs_dir_path)
    os.makedirs(abs_dir_path, exist_ok=True)
    git.ensure_github_repo(repo_url=url)

    # pull branch and set env for neon
    result = git.clone(url, destination=abs_dir_path)
    logger.debug(f"\nClone result: {result['success']}")

    if result['success']:
        # setup neon
        branch_info = neon.fork(project_name=proj_name, branch_name=branch_name)

        if not isinstance(branch_info, Exception):
            write_connection_to_env(branch_info, os.path.join(abs_dir_path, ".env"))
        else:
            raise branch_info

        return branch_info
    else:
        raise ValueError(f"Could not clone repository, {result["stderr"]}")


def post_agent_run(branch_info: BranchInfo, dir_path: str):
    # Convert to absolute path for consistency
    abs_dir_path = os.path.abspath(dir_path)

    add_scripts_to_package_json(abs_dir_path)
    start_server_background(abs_dir_path)
    # delete neon
    try:
        neon.promote(
            branch_info.user,
            branch_info.project_id,
            branch_info.endpoint_id,
            branch_info.id,
        )
    except Exception as e:
        raise e
    


async def agent_run(dir_path: str, prompt: str, first: bool = False):
    if first:
        system_prompt = read(first)
        first = False
    else:
        system_prompt = read(first)
    # run agent
    messages_count: int = 0
    tool_uses_count: int = 0
    result = None  # Initialize result to avoid UnboundLocalError
    options = ClaudeAgentOptions(
        system_prompt=system_prompt, permission_mode="bypassPermissions", cwd=dir_path
    )

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            messages_count += 1
            for block in message.content:
                if isinstance(block, TextBlock):
                    logger.info(f" Claude: {block.text}...")
                    # Check for API errors in the text block
                    if "API Error" in block.text or "api error" in block.text.lower():
                        error_message = block.text
                        logger.error(f"API Response Error: {error_message}")
                elif isinstance(block, ThinkingBlock):
                    logger.info(f"Thinking: {block.thinking}...")
                elif isinstance(block, ToolUseBlock):
                    tool_uses_count += 1
                    logger.info(f"Tool: {block.name} Input: {block.input}")
                elif isinstance(block, ToolResultBlock):
                    if block.is_error:
                        logger.error("Tool error occurred")
                    logger.info(
                        f"Tool Result Id: {block.tool_use_id}, Content: {block.content}"
                    )
        elif isinstance(message, ResultMessage):
            result = message
            logger.info("Received result message")
        logger.info(message)
    return result


@app.post("/api/execute")
async def execute_endpoint(request: ExecuteRequest) -> ExecuteResponse:
    try:
        result = await execute(
            url=request.url,
            proj_name=request.projectName,
            branch_name=request.branchName,
            dir_path=request.dirPath,
            prompt=request.prompt,
            first=request.first
        )

        # Return success response with result details
        return ExecuteResponse(
            success=True,
            message=str(result),
            previewUrl="http://localhost:3000"
        )
    except Exception as e:
        logger.error(f"Execute endpoint error: {str(e)}")
        return ExecuteResponse(
            success=False,
            message=str(e),
            previewUrl=None
        ) 

async def execute(url: str, proj_name: str, branch_name: str, dir_path: str, prompt: str, first: bool = False) -> ResultMessage:
    # Convert to absolute path once at the beginning
    abs_dir_path = os.path.abspath(dir_path)

    # Pre-Agent Run
    branch_info = pre_agent_run(url, proj_name, branch_name, abs_dir_path)

    # Run
    result = await agent_run(abs_dir_path, prompt, first)
    logger.info("===" * 60)
    logger.info(result)
    logger.info("===" * 60)

    # Post-Agent Run
    if isinstance(branch_info, BranchInfo):
        post_agent_run(branch_info, abs_dir_path)

    return result

def test():
    repo = None
    proj_name = None
    branch_name = None
    dir_path = None
    for idx, arg in enumerate(sys.argv):
        if idx > 0 and idx % 2 != 0:
            if arg == "--projectname" or arg == "-p":
                repo = sys.argv[idx + 1]
            elif arg == "--username" or arg == "-u":
                proj_name = sys.argv[idx + 1]
            elif arg == "--featurename" or arg == "-f":
                branch_name = sys.argv[idx + 1]
            elif arg == "--dir-path" or arg == "-d":
                dir_path = sys.argv[idx + 1]

    first = True
    if not repo or not proj_name or not branch_name or not dir_path:
        print(
            dedent("""
            Run using the following flags set
            --projectname or -p: Project name
            --username or -u: Username
            --featurename or -f: Feature Name
            --dir-path or -d: Temp Local Directory
        """).strip()
        )
    else:
        GIT_URL = "git@github.com:shnkreddy98"
        github_url = f"{GIT_URL}/{repo}.git"
        prompt = input("What is up?\n> ")
        asyncio.run(execute(github_url, proj_name, branch_name, dir_path, prompt, first))

if __name__ == "__main__":
    uvicorn.run(app=app, port=8080)