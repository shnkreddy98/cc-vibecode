import httpx
import os
import psycopg2 #type: ignore
import time

from cc_vibecode.logger import create_logger

from dotenv import load_dotenv
from neon_api import NeonAPI #type: ignore
from neon_api.schema import ( #type: ignore
    Branch1,
    Database,
    ProjectListItem,
    Endpoint,
    EndpointState,
    Role,
    Project,
)
from pydantic import BaseModel

load_dotenv("env_vars/.env")
logger = create_logger("neon")


class BranchInfo(BaseModel):
    id: str
    name: str
    database: str
    user: str
    password: str | None
    host: str
    project_id: str
    endpoint_id: str


class CustomNeonAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.neon = NeonAPI(api_key=self.api_key)
        self.BASE_URL = "https://console.neon.tech/api/v2"

    def _wait_for_branch_ready(
        self, proj_id: str, branch_id: str, timeout: int = 60
    ) -> bool:
        """Wait for branch to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            branch_response = self.neon.branch(proj_id, branch_id)
            branch = branch_response.branch  # type: ignore
            if branch.current_state == "ready":
                logger.info(f"Branch {branch_id} is ready")
                return True
            logger.info(f"Waiting for branch... current state: {branch.current_state}")
            time.sleep(2)
        return False

    def _wait_for_endpoint_active(
        self, proj_id: str, endpoint_id: str, timeout: int = 60
    ) -> bool:
        """Wait for endpoint to be active"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            endpoint_response = self.neon.endpoint(proj_id, endpoint_id)
            endpoint = endpoint_response.endpoint  # type: ignore
            if endpoint.current_state == EndpointState.active:
                logger.info(f"Endpoint {endpoint_id} is active")
                return True
            logger.info(
                f"Waiting for endpoint... current state: {endpoint.current_state}"
            )
            time.sleep(2)
        return False

    def _get_project(self, proj_id: str) -> dict | None:
        url = f"{self.BASE_URL}/projects/{proj_id}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        with httpx.Client() as client:
            res = client.get(
                url=url,
                headers=headers,
            )

        if 200 <= res.status_code <= 299:
            return res.json()

        return None

    def _wait_for_project_ready(self, proj_id: str, timeout: int = 120) -> bool:
        """Wait for project to be ready after creation"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                project_response = self._get_project(proj_id)
                if project_response:
                    project_id = project_response.get("project", {}).get("id", "")
                    if project_id == proj_id:
                        return True

                # Check if we can list branches (means project is ready)
                self.neon.branches(proj_id)
                logger.info(f"Project {proj_id} is ready")
                return True
            except Exception as e:
                logger.info(f"Waiting for project... {str(e)}")
                time.sleep(3)
        return False

    def _launch_branch(
        self, proj_id: str, name: str, max_retries: int = 10
    ) -> Branch1 | Exception:
        args = {
            "branch": {"name": f"{name}_branch"},
        }

        for attempt in range(max_retries):
            try:
                results_response = self.neon.branch_create(proj_id, **args)
                return results_response.branch  # type: ignore
            except Exception as e:
                error_str = str(e)

                # Handle project locked (423)
                if "423" in error_str or "conflicting operations" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = 5 * (attempt + 1)  # Exponential backoff
                        logger.info(
                            f"Project locked, waiting {wait_time}s before retry {attempt + 1}/{max_retries}"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error("Max retries reached, project still locked")
                        raise e
                else:
                    # For any other error, raise it immediately
                    raise e

        # If we exit the loop without returning, something went wrong
        raise Exception(f"Failed to create or retrieve branch after {max_retries} attempts")

    def _get_projects(self) -> list[ProjectListItem]:
        project_response = self.neon.projects()
        return project_response.projects  # type: ignore

    def _get_database(self, proj_id: str, branch_id: str) -> Database:
        databases_response = self.neon.databases(proj_id, branch_id)
        return databases_response.databases[0]  # type: ignore

    def _create_endpoint(self, proj_id: str, branch_id: str, name: str) -> Endpoint:
        args = {
            "endpoint": {
                "type": "read_write",
                "branch_id": branch_id,
                "name": f"{name}_endpoint",
            }
        }
        endpoint_response = self.neon.endpoint_create(proj_id, **args)
        return endpoint_response.endpoint  # type: ignore

    def _create_role(self, proj_id: str, branch_id: str, role_name: str) -> Role:
        role_response = self.neon.role_create(proj_id, branch_id, role_name)
        return role_response.role  # type: ignore

    def _schema_diff(
        self, proj_id: str, branch_id: str, base_branch_id: str, db_name: str
    ):
        url = f"{self.BASE_URL}/projects/{proj_id}/branches/{branch_id}/compare_schema"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        params = {"base_branch_id": base_branch_id, "db_name": db_name}
        with httpx.Client() as client:
            res = client.get(url=url, headers=headers, params=params)

        if 200 <= res.status_code <= 299:
            return res.json()

    def _grant_schema_permissions(self, connection_string: str, role_name: str):
        """Grant CREATE permissions using an existing owner connection"""
        try:
            conn = psycopg2.connect(connection_string)
            conn.autocommit = True
            cursor = conn.cursor()

            # Quote role names to handle special characters like hyphens
            cursor.execute(f'GRANT CREATE ON SCHEMA public TO "{role_name}";')
            cursor.execute(
                f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{role_name}";'
            )
            cursor.execute(
                f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{role_name}";'
            )

            logger.info(f"✓ Granted permissions to {role_name}")
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"✗ Error: {e}")
            return False

    def _delete_role(self, proj_id: str, branch_id: str, role_name: str):
        return self.neon.role_delete(proj_id, branch_id, role_name)

    def _delete_endpoint(self, proj_id: str, endpoint_id: str):
        return self.neon.endpoint_delete(proj_id, endpoint_id)

    def _delete_branch(self, proj_id: str, branch_id: str):
        return self.neon.branch_delete(proj_id, branch_id)

    def _promote_to_main(self, proj_id: str, branch_id: str):
        url = f"{self.BASE_URL}/projects/{proj_id}/branches/{branch_id}/set_as_default"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        with httpx.Client() as client:
            res = client.post(
                url=url,
                headers=headers,
            )

        if 200 <= res.status_code <= 299:
            return res.json()

    def _create_project(self, project_name: str, branch_name: str) -> Project:
        data = {
            "project": {
                "branch": {
                    "name": branch_name,
                },
                "pg_version": 17,
                "name": project_name,
            }
        }
        project_response = self.neon.project_create(**data)
        return project_response.project  # type: ignore

    def fork(self, project_name: str, branch_name: str) -> BranchInfo | Exception:
        projects = self._get_projects()
        if len(projects) == 0:
            logger.info("No Projects found, creating one..")
            project = self._create_project(
                project_name=project_name, branch_name=branch_name
            )

            # Wait for project to be ready
            if not self._wait_for_project_ready(project.id):
                logger.error("Timeout waiting for project to be ready")
        else:
            logger.info("Found project, selecting one...")
            project = projects[0]

        # Create Branch
        branch = self._launch_branch(project.id, branch_name)
        if isinstance(branch, Exception):
            raise branch
        logger.info(f"Branch Created with id: {branch.id}")

        # Wait for branch to be ready
        if not self._wait_for_branch_ready(project.id, branch.id):
            logger.info("Timeout waiting for branch to be ready")
            raise Exception("Branch not ready")

        # Get database
        database = self._get_database(project.id, branch.id)

        # Create Endpoint FIRST (required for role operations)
        endpoint = self._create_endpoint(project.id, branch.id, branch_name)
        logger.info(f"Endpoint created with id: {endpoint.id}")

        # Wait for endpoint to be active
        if not self._wait_for_endpoint_active(project.id, endpoint.id):
            logger.info("Timeout waiting for endpoint to be active")
            raise Exception("Endpoint not active")

        # NOW we can get and reset the owner role password
        roles_response = self.neon.roles(project.id, branch.id)
        owner_role = None
        for role in roles_response.roles:  # type: ignore
            if role.protected or "_owner" in role.name:
                owner_role = role
                break

        if not owner_role:
            owner_role = roles_response.roles[0]  # type: ignore

        # Reset owner password (endpoint must exist first!)
        logger.info(f"Resetting password for owner role: {owner_role.name}")
        owner_reset_response = self.neon.role_password_reset(
            project.id, branch.id, owner_role.name
        )
        owner_role = owner_reset_response.role  # type: ignore
        logger.info("✓ Owner password reset")

        # Create the owner connection string
        owner_connection_string = f"postgresql://{owner_role.name}:{owner_role.password}@{endpoint.host}/{database.name}"

        # Create new Role
        role = self._create_role(project.id, branch.id, branch_name)
        logger.info(f"Role created with name: {role.name}")

        # Grant permissions
        self._grant_schema_permissions(owner_connection_string, role.name)

        return BranchInfo(
            id=branch.id,
            name=branch.name,
            database=database.name,
            user=role.name,
            password=role.password,
            host=endpoint.host,
            project_id=project.id,
            endpoint_id=endpoint.id,
        )

    def promote(
        self, role_name: str, project_id: str, endpoint_id: str, branch_id: str
    ):
        # remove role
        logger.info(self._delete_role(project_id, branch_id, role_name))

        # remove endpoint
        logger.info(self._delete_endpoint(project_id, endpoint_id))

        # promote branch
        logger.info(self._promote_to_main(project_id, branch_id))

        # remove old main branch?


if __name__ == "__main__":
    api_key = os.getenv("NEON_API_KEY", "")
    neon = CustomNeonAPI(api_key=api_key)

    project_name = "new"
    branch_name = "test"
    creds = neon.fork(project_name, branch_name)
    print(creds)

    if isinstance(creds, BranchInfo):
        neon.promote(creds.name, creds.project_id, creds.endpoint_id, creds.id)
