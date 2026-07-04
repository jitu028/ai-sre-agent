import pytest
from agents.incident_agent import create_incident_agent

def test_agent_creation():
    agent = create_incident_agent()
    assert agent is not None
    assert agent.name == "IncidentResponseAgent"
    assert "IncidentResponseAgent" in agent.instruction
    assert len(agent.tools) == 7
    
    # Check that expected tools are present
    tool_names = [t.__name__ if hasattr(t, '__name__') else str(t) for t in agent.tools]
    assert "read_recent_logs" in tool_names
    assert "read_error_logs" in tool_names
    assert "read_metrics" in tool_names
    assert "list_revisions" in tool_names
    assert "describe_revision" in tool_names
    assert "rollback_revision" in tool_names
    assert "verify_service_health" in tool_names
