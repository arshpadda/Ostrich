import logging
import os
import shutil
import subprocess

import requests
from google.cloud import storage
from langchain_core.tools import tool

logger = logging.getLogger("sandbox-agent")


@tool
def get_weather(location: str) -> str:
    """Gets the current weather for a specific location. Use this when the user asks about the weather."""
    try:
        logger.info(f"Executing tool get_weather for {location}...")
        headers = {"User-Agent": "curl/8.6.0"}
        response = requests.get(f"https://wttr.in/{location}?format=3", headers=headers, timeout=5)
        response.raise_for_status()
        logger.info(f"Weather fetched successfully: {response.text.strip()}")
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error executing get_weather: {str(e)}")
        return f"Could not fetch weather for {location}: {str(e)}"


@tool
def execute_bash(command: str) -> str:
    """Executes a bash command in the terminal and returns the output. Use this to install packages, run tests, or inspect the environment."""
    try:
        logger.info(f"Executing bash: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        return output.strip() if output else "Command executed successfully (no output)."
    except subprocess.TimeoutExpired:
        return "Command timed out after 60 seconds."
    except Exception as e:
        return f"Bash execution failed: {str(e)}"


@tool
def read_file(filepath: str) -> str:
    """Reads the contents of a file."""
    try:
        with open(filepath, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(filepath: str, content: str) -> str:
    """Writes content to a file. Overwrites the file if it exists."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)) or ".", exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
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
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"{user_id}/workspace.zip")
        blob.upload_from_filename(zip_file)

        # Clean up the zip file from tmp
        os.remove(zip_file)

        msg = f"Successfully uploaded workspace to gs://{bucket_name}/{user_id}/workspace.zip"
        logger.info(msg)
        return msg
    except Exception as e:
        logger.error(f"Failed to save workspace: {str(e)}")
        return f"Failed to save workspace: {str(e)}"
