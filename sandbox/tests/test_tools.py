import json
import os

from src.tools import execute_bash, read_file, write_file


def test_write_and_read_file(tmp_path):
    """Test that writing and reading files works correctly."""
    test_file = tmp_path / "test.txt"
    content = "Hello, Sandbox!"

    # Test writing
    write_result = write_file.invoke({"filepath": str(test_file), "content": content})
    assert "Successfully wrote to" in write_result
    assert os.path.exists(test_file)

    # Test reading
    read_result = json.loads(read_file.invoke({"filepath": str(test_file)}))
    assert read_result["status"] == "success"
    assert read_result["data"] == content


def test_execute_bash():
    """Test executing a simple bash command."""
    # Test a successful command
    result = execute_bash.invoke({"command": "echo 'Testing 123'"})
    assert "Testing 123" in result

    # Test a failing command
    result = execute_bash.invoke({"command": "nonexistent_command_123"})
    # It should return the stderr output or a failure message, not crash
    assert "not found" in result or "Bash execution failed" in result or "Command executed successfully" not in result
