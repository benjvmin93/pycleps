import pytest
from ParamikoMock import SSHCommandMock, ParamikoMockEnviron, SSHClientMock
from unittest.mock import patch
from pycleps.cleps_ssh_wrapper import ClepsSSHWrapper

USERNAME = "root"
PASSWORD = "root"
HOSTNAME = "cleps.inria.fr"

def add_response(mock: ParamikoMockEnviron, responses: dict[str, 'SSHResponseMock']) -> None:
    mock.add_responses_for_host(HOSTNAME, 22, responses, USERNAME, PASSWORD)

@pytest.fixture
def mock_env():
    return ParamikoMockEnviron()

def test_init_echo(mock_env):
    add_response(mock_env, {"re(^echo .*?$)": SSHCommandMock("", "hello", "")})

    with patch("pycleps.cleps_ssh_wrapper.paramiko.SSHClient", new=SSHClientMock):
        wrapper = ClepsSSHWrapper(hostname=HOSTNAME, wd=".", username=USERNAME, password=PASSWORD)
        output = wrapper.exec_cmd("echo hello")
        
        assert output == "hello"  # Ensure expected output
        mock_env.assert_command_was_executed(HOSTNAME, 22, "echo hello")

    mock_env.cleanup_environment()
