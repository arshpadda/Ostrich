import json
import logging
import os
import shutil
import subprocess

import requests
from google.cloud import storage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger("sandbox-agent")


class GetWeatherInput(BaseModel):
    location: str = Field(description="The city and state, e.g., San Francisco, CA")


@tool(args_schema=GetWeatherInput)
def get_weather(location: str) -> str:
    """Gets the current weather for a specific location. Use this when the user asks about the weather."""
    try:
        logger.info(f"Executing tool get_weather for {location}...")
        headers = {"User-Agent": "curl/8.6.0"}
        response = requests.get(f"https://wttr.in/{location}?format=3", headers=headers, timeout=5)
        response.raise_for_status()
        logger.info(f"Weather fetched successfully: {response.text.strip()}")
        return json.dumps({"status": "success", "data": response.text.strip(), "error_message": None})
    except requests.RequestException as e:
        logger.error(f"Error executing get_weather: {str(e)}")
        return json.dumps(
            {"status": "error", "data": None, "error_message": f"Could not fetch weather for {location}: {str(e)}"}
        )


class ExecuteBashInput(BaseModel):
    command: str = Field(description="The bash command to execute.")


@tool(args_schema=ExecuteBashInput)
def execute_bash(command: str) -> str:
    """Executes a bash command in the terminal and returns the output. Use this to install packages, run tests, or inspect the environment."""
    try:
        logger.info(f"Executing bash: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        output_str = output.strip() if output else "Command executed successfully (no output)."
        return json.dumps({"status": "success", "data": output_str, "error_message": None})
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "error", "data": None, "error_message": "Command timed out after 60 seconds."})
    except subprocess.SubprocessError as e:
        return json.dumps({"status": "error", "data": None, "error_message": f"Bash execution failed: {str(e)}"})


class ReadFileInput(BaseModel):
    filepath: str = Field(description="The absolute or relative path to the file to read.")


@tool(args_schema=ReadFileInput)
def read_file(filepath: str) -> str:
    """Reads the contents of a file."""
    try:
        with open(filepath, "r") as f:
            content = f.read()
        return json.dumps({"status": "success", "data": content, "error_message": None})
    except FileNotFoundError:
        return json.dumps({"status": "error", "data": None, "error_message": f"File not found: {filepath}"})
    except PermissionError:
        return json.dumps(
            {"status": "error", "data": None, "error_message": f"Permission denied reading file: {filepath}"}
        )
    except OSError as e:
        return json.dumps({"status": "error", "data": None, "error_message": f"OS error reading file: {str(e)}"})


class WriteFileInput(BaseModel):
    filepath: str = Field(description="The path to the file to write to.")
    content: str = Field(description="The content to write to the file.")


@tool(args_schema=WriteFileInput)
def write_file(filepath: str, content: str) -> str:
    """Writes content to a file. Overwrites the file if it exists."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)) or ".", exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        return json.dumps({"status": "success", "data": f"Successfully wrote to {filepath}", "error_message": None})
    except PermissionError:
        return json.dumps(
            {"status": "error", "data": None, "error_message": f"Permission denied writing to file: {filepath}"}
        )
    except OSError as e:
        return json.dumps({"status": "error", "data": None, "error_message": f"OS error writing file: {str(e)}"})


class SaveWorkspaceInput(BaseModel):
    pass  # No arguments required


@tool(args_schema=SaveWorkspaceInput)
def save_workspace() -> str:
    """Zips the /workspace directory and uploads it to Google Cloud Storage. YOU MUST CALL THIS TOOL as your final action when you have finished your coding task."""
    try:
        bucket_name = os.getenv("GCS_BUCKET_NAME", "ostrich-agent-workspaces")
        user_id = os.getenv("USER_ID", "local-test")

        logger.info(f"Zipping /workspace for user {user_id}...")
        zip_path = "/tmp/workspace"
        shutil.make_archive(zip_path, "zip", "/workspace")
        zip_file = f"{zip_path}.zip"

        logger.info(f"Uploading {zip_file} to gs://{bucket_name}/{user_id}/workspace.zip ...")

        # Check if we have credentials, otherwise skip upload to avoid 10s timeout
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and "cloud.google.com" not in os.environ:
            # We are likely running in a local Minikube environment without ADC.
            # Skip the actual upload.
            logger.warning("No Google Application Credentials found, skipping GCS upload.")
            os.remove(zip_file)
            return json.dumps(
                {
                    "status": "success",
                    "data": "Workspace zipped successfully (upload skipped due to local environment)",
                    "error_message": None,
                }
            )

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"{user_id}/workspace.zip")
        blob.upload_from_filename(zip_file)

        # Clean up the zip file from tmp
        os.remove(zip_file)

        msg = f"Successfully uploaded workspace to gs://{bucket_name}/{user_id}/workspace.zip"
        logger.info(msg)
        return json.dumps({"status": "success", "data": msg, "error_message": None})
    except Exception as e:  # Using broad exception here because storage errors can be numerous
        logger.error(f"Failed to save workspace: {str(e)}")
        return json.dumps({"status": "error", "data": None, "error_message": f"Failed to save workspace: {str(e)}"})
