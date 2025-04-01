import pytest
from ParamikoMock import (
    SSHCommandMock,
    ParamikoMockEnviron,
    SSHClientMock,
    SSHResponseMock,
)
from unittest.mock import patch
from pycleps.cleps_ssh_wrapper import ClepsSSHWrapper
from pathlib import Path

USERNAME = "root"
PASSWORD = "root"
HOSTNAME = "cleps.inria.fr"


def add_response(
    mock: ParamikoMockEnviron, responses: dict[str, SSHResponseMock]
) -> None:
    mock.add_responses_for_host(HOSTNAME, 22, responses, USERNAME, PASSWORD)


@pytest.fixture
def mock_env():
    return ParamikoMockEnviron()

def test_init_echo(mock_env):
    add_response(mock_env, {"re(^echo .*?$)": SSHCommandMock("", "hello", "")})

    with patch("pycleps.cleps_ssh_wrapper.paramiko.SSHClient", new=SSHClientMock):
        wrapper = ClepsSSHWrapper(wd=Path.home(), username=USERNAME, password=PASSWORD)
        output = wrapper.exec_cmd("echo hello")
        assert output == "hello"  # Ensure expected output
        mock_env.assert_command_was_executed(HOSTNAME, 22, "echo hello")

    mock_env.cleanup_environment()


@pytest.mark.parametrize(
    "repo_url",
    [
        "https://github.com/TeamGraphix/graphix.git",
        "git@github.com:TeamGraphix/graphix.git",
    ],
)
def test_clone_repo(mock_env, repo_url):
    wd = Path.home()

    mkdir_cmd = f"mkdir -p {wd}"
    git_clone_cmd = f"git clone {repo_url} /home/benjamin/graphix"

    add_response(
        mock_env,
        {
            f"re(^{mkdir_cmd}$)": SSHCommandMock("", "", ""),
            f"re(^{git_clone_cmd}$)": SSHCommandMock("", "", ""),
        },
    )

    with patch("pycleps.cleps_ssh_wrapper.paramiko.SSHClient", new=SSHClientMock):
        wrapper = ClepsSSHWrapper(wd=wd, username=USERNAME, password=PASSWORD)
        wrapper.clone_repo(repo_url)
        
        mock_env.assert_command_was_executed(HOSTNAME, 22, mkdir_cmd)
        mock_env.assert_command_was_executed(HOSTNAME, 22, git_clone_cmd)

    mock_env.cleanup_environment()


def test_clone_repo_already_existing(mock_env):
    """Simulate error when repo already exists."""
    repo_url = "https://github.com/example/repo.git"
    wd = Path.home()
    mkdir_cmd = f"mkdir -p {wd}"
    git_clone_cmd = f"git clone {repo_url} /home/benjamin/repo"

    add_response(
        mock_env,
        {
            f"re(^{mkdir_cmd}$)": SSHCommandMock("", "", ""),
            "mkdir ~/repo": SSHCommandMock("", "", ""),
            f"re(^{git_clone_cmd}$)": SSHCommandMock(
                "",
                "",
                "fatal: destination path 'repo' already exists and is not an empty directory.",
            ),
        },
    )

    with patch("pycleps.cleps_ssh_wrapper.paramiko.SSHClient", new=SSHClientMock):
        wrapper = ClepsSSHWrapper(wd=wd, username=USERNAME, password=PASSWORD)
        # Expect exception handling, but no crash
        with pytest.raises(Exception):
            wrapper.clone_repo(repo_url)

    mock_env.cleanup_environment()


def test_clone_repo_with_branch(mock_env):
    repo_url = "https://github.com/benjvmin93/pycleps.git"
    git_branch = "env-integration"
    wd = Path(".")

    mkdir_cmd = f"mkdir -p {wd}"
    git_clone_cmd = f"git clone {repo_url} pycleps"
    git_checkout_cmd = f"git -C {wd / 'pycleps'} checkout {git_branch}"

    add_response(
        mock_env,
        {
            f"re(^{mkdir_cmd}$)": SSHCommandMock("", "", ""),
            f"re(^{git_clone_cmd}$)": SSHCommandMock("", "", ""),
            f"re(^{git_checkout_cmd}$)": SSHCommandMock("", "", ""),
        },
    )

    with patch("pycleps.cleps_ssh_wrapper.paramiko.SSHClient", new=SSHClientMock):
        wrapper = ClepsSSHWrapper(wd=wd, username=USERNAME, password=PASSWORD)
        wrapper.clone_repo(repo_addr=repo_url, git_branch=git_branch)

    mock_env.cleanup_environment()
