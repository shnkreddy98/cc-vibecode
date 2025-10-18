import asyncio
import os
import sys
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
from airfold_apps.git import CustomGitAPI
from airfold_apps.neon import CustomNeonAPI, BranchInfo
from airfold_apps.logger import create_logger

logger = create_logger("agent")

git = CustomGitAPI(os.getenv("GITHUB_TOKEN", ""))
neon = CustomNeonAPI(os.getenv("NEON_API_KEY", ""))


def read(first: bool = False):
    with open("prompts.yaml", "r") as f:
        prompts = yaml.safe_load(f)

    if first:
        return prompts["first_prompt"]
    else:
        return prompts["therest_prompt"]


def write_connection_to_env(connection: BranchInfo, env_path: str = ".env"):
    with open(env_path, "a+") as f:
        f.write(f"\nDATABASE={connection.database}\n")
        f.write(f"USER={connection.user}\n")
        f.write(f"PASSWORD={connection.password}\n")
        f.write(f"HOST={connection.host}\n")


def pre_agent_run(
    url: str, proj_name: str, branch_name: str, dir_path: str
) -> BranchInfo | Exception:
    # init git and neon
    # if not exists create git and neon
    # Clean up existing directory from previous runs
    if os.path.exists(dir_path):
        import shutil
        shutil.rmtree(dir_path)
    os.makedirs(dir_path, exist_ok=True)
    git.ensure_github_repo(repo_url=url)

    # pull branch and set env for neon
    result = git.clone(url, destination=dir_path)
    logger.debug(f"\nClone result: {result['success']}")

    if result['success']:
        # setup neon
        branch_info = neon.fork(project_name=proj_name, branch_name=branch_name)

        if not isinstance(branch_info, Exception):
            write_connection_to_env(branch_info, os.path.join(dir_path, ".env"))
        else:
            raise branch_info

        return branch_info
    else:
        raise ValueError(f"Could not clone repository, {result["stderr"]}")


def post_agent_run(branch_info: BranchInfo):
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


async def execute(url: str, proj_name: str, branch_name: str, dir_path: str, prompt: str, first: bool = False):
    # Pre-Agent Run
    branch_info = pre_agent_run(url, proj_name, branch_name, dir_path)

    # Run
    result = await agent_run(dir_path, prompt, first)
    logger.info("===" * 60)
    logger.info(result)
    logger.info("===" * 60)

    # Post-Agent Run
    if isinstance(branch_info, BranchInfo):
        post_agent_run(branch_info)


if __name__ == "__main__":
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
