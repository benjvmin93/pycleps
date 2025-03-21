import pytest
from ParamikoMock import SSHCommandMock, ParamikoMockEnviron, SSHClientMock
from unittest.mock import patch
from pycleps.cleps_ssh_wrapper import ClepsSSHWrapper

@pytest.fixture
def mock_env():
    return ParamikoMockEnviron()

def test_init_echo(mock_env):
    username = "root"
    password = "root"
    hostname = "cleps.inria.fr"
    
    mock_env.add_responses_for_host(
        hostname, 22, {"re(^echo .*?$)": SSHCommandMock("", "hello", "")}, username, password
    )

    with patch("pycleps.cleps_ssh_wrapper.paramiko.SSHClient", new=SSHClientMock):
        wrapper = ClepsSSHWrapper(hostname=hostname, wd=".", username=username, password=password)
        output = wrapper.exec_cmd("echo hello")
        
        assert output == "hello"  # Ensure expected output
        mock_env.assert_command_was_executed(hostname, 22, "echo hello")

    mock_env.cleanup_environment()
