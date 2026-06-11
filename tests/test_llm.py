from simple_coding_agent.llm import parse_tool_calls


def test_parse_single_tool_call():
    calls = parse_tool_calls('{"tool": "read_file", "arguments": {"path": "README.md"}}')
    assert len(calls) == 1
    assert calls[0].name == "read_file"
    assert calls[0].arguments == {"path": "README.md"}


def test_parse_multiple_tool_calls_from_fenced_json():
    calls = parse_tool_calls(
        '```json\n{"tools": [{"tool": "list_files", "arguments": {}}, {"tool": "search", "arguments": {"pattern": "TODO"}}]}\n```'
    )
    assert [call.name for call in calls] == ["list_files", "search"]
