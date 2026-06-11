from simple_coding_agent.agent import CodingAgent
from simple_coding_agent.llm import MockClient
from simple_coding_agent.types import AgentConfig


def test_agent_runs_in_mock_mode(tmp_path):
    config = AgentConfig(workspace=tmp_path, model="mock", mock=True, max_steps=4)
    final = CodingAgent(config, MockClient()).run("create a demo")
    assert "Done" in final
    assert (tmp_path / "README.md").exists()
    assert list((tmp_path / ".simple-agent" / "runs").glob("*.json"))
