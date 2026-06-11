from simple_coding_agent.tools import WorkspaceTools


def test_write_and_read_file_stays_in_workspace(tmp_path):
    tools = WorkspaceTools(tmp_path)
    write = tools.write_file({"path": "notes/demo.txt", "content": "hello"})
    assert write.ok
    read = tools.read_file({"path": "notes/demo.txt"})
    assert read.ok
    assert read.output == "hello"


def test_rejects_path_escape(tmp_path):
    tools = WorkspaceTools(tmp_path)
    result = tools.write_file({"path": "../escape.txt", "content": "nope"})
    assert not result.ok
    assert "escapes workspace" in result.output


def test_destructive_shell_needs_yes(tmp_path):
    tools = WorkspaceTools(tmp_path, auto_yes=False)
    result = tools.run_shell({"command": "rm -rf something"})
    assert not result.ok
    assert "without --yes" in result.output
