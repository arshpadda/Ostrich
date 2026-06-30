import json

from src.tools import execute_bash, read_file, write_file


def test_write_and_read_file(tmp_path, monkeypatch):
    """Writing and reading files works correctly within the workspace."""
    monkeypatch.setenv("WORKSPACE_DIR", str(tmp_path))
    content = "Hello, Sandbox!"

    write_result = write_file.invoke({"filepath": "test.txt", "content": content})
    assert "Successfully wrote to" in write_result
    assert (tmp_path / "test.txt").exists()

    read_result = json.loads(read_file.invoke({"filepath": "test.txt"}))
    assert read_result["status"] == "success"
    assert read_result["data"] == content


def test_file_tools_reject_escape(tmp_path, monkeypatch):
    """Paths outside the workspace (absolute or via ..) are rejected."""
    monkeypatch.setenv("WORKSPACE_DIR", str(tmp_path))

    abs_escape = json.loads(write_file.invoke({"filepath": "/etc/pwned", "content": "x"}))
    assert abs_escape["status"] == "error"
    assert "outside the workspace" in abs_escape["error_message"]

    rel_escape = json.loads(read_file.invoke({"filepath": "../../../etc/passwd"}))
    assert rel_escape["status"] == "error"
    assert "outside the workspace" in rel_escape["error_message"]


def test_read_file_truncates_large(tmp_path, monkeypatch):
    """read_file caps the number of bytes returned."""
    monkeypatch.setenv("WORKSPACE_DIR", str(tmp_path))
    write_file.invoke({"filepath": "big.txt", "content": "a" * (300 * 1024)})

    result = json.loads(read_file.invoke({"filepath": "big.txt"}))
    assert result["status"] == "success"
    assert result["data"].endswith("...[truncated]")
    assert len(result["data"]) <= 256 * 1024 + 32


def test_execute_bash():
    """Executing a simple bash command works; failures don't crash."""
    result = execute_bash.invoke({"command": "echo 'Testing 123'"})
    assert "Testing 123" in result

    result = execute_bash.invoke({"command": "nonexistent_command_123"})
    assert "not found" in result or "Bash execution failed" in result or "Command executed successfully" not in result


def test_execute_bash_truncates_output():
    """execute_bash truncates very large output."""
    result = json.loads(execute_bash.invoke({"command": "for i in $(seq 1 5000); do echo xxxxxxxxxx; done"}))
    assert result["status"] == "success"
    assert "[output truncated]" in result["data"]
