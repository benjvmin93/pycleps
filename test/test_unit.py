import pytest
from ParamikoMock import (
    SSHCommandMock,
    ParamikoMockEnviron,
    SSHClientMock,
    SSHResponseMock,
)
from unittest.mock import patch
from pycleps.cleps_ssh_wrapper import ClepsSSHWrapper

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


@pytest.fixture
def ssh_wrapper(mock_env):
    """Creates a patched SSH wrapper instance."""
    with patch("pycleps.cleps_ssh_wrapper.paramiko.SSHClient", new=SSHClientMock):
        return ClepsSSHWrapper(wd=".", username=USERNAME, password=PASSWORD)


def test_init_echo(mock_env):
    add_response(mock_env, {"re(^echo .*?$)": SSHCommandMock("", "hello", "")})

    with patch("pycleps.cleps_ssh_wrapper.paramiko.SSHClient", new=SSHClientMock):
        wrapper = ClepsSSHWrapper(wd=".", username=USERNAME, password=PASSWORD)
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
    dst_dir = "~/repo"
    wd = "."

    git_clone_cmd = f"git clone {repo_url} {dst_dir}"
    mkdir_cmd = f"mkdir -p {wd}"

    add_response(
        mock_env,
        {
            f"re(^{git_clone_cmd}$)": SSHCommandMock("", "Cloning into 'repo'...", ""),
            f"re(^{mkdir_cmd}$)": SSHCommandMock("", "", ""),
        },
    )

    with patch("pycleps.cleps_ssh_wrapper.paramiko.SSHClient", new=SSHClientMock):
        wrapper = ClepsSSHWrapper(wd=wd, username=USERNAME, password=PASSWORD)
        wrapper.clone_repo(repo_url, dst_dir)

        mock_env.assert_command_was_executed(HOSTNAME, 22, git_clone_cmd)
        mock_env.assert_command_was_executed(HOSTNAME, 22, mkdir_cmd)

    mock_env.cleanup_environment()


def test_clone_repo_already_existing(mock_env):
    """Simulate error when repo already exists."""
    repo_url = "https://github.com/example/repo.git"
    dst_dir = "~/repo"
    wd = "."

    git_clone_cmd = f"git clone {repo_url} {dst_dir}"
    mkdir_cmd = f"mkdir -p {wd}"

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
        wrapper = ClepsSSHWrapper(wd=".", username=USERNAME, password=PASSWORD)
        wrapper.exec_cmd("mkdir ~/repo")

        # Expect exception handling, but no crash
        wrapper.clone_repo(repo_url, dst_dir)

        mock_env.assert_command_was_executed(HOSTNAME, 22, git_clone_cmd)

    mock_env.cleanup_environment()


def test_clone_repo_with_branch(mock_env):
    repo_url = "https://github.com/example/repo.git"
    dst_dir = "~/repo"
    git_branch = "dm-simu-rs"
    wd = "."

    git_clone_cmd = f"git clone {repo_url} {dst_dir}"
    git_checkout_cmd = f"git -C {dst_dir} checkout {git_branch}"
    mkdir_cmd = f"mkdir -p {wd}"

    add_response(
        mock_env,
        {
            f"re(^{mkdir_cmd}$)": SSHCommandMock("", "", ""),
            f"re(^{git_clone_cmd}$)": SSHCommandMock("", "Cloning into 'repo'...", ""),
            f"re(^{git_checkout_cmd}$)": SSHCommandMock(
                "", f"Switched to branch '{git_branch}'", ""
            ),
        },
    )

    with patch("pycleps.cleps_ssh_wrapper.paramiko.SSHClient", new=SSHClientMock):
        wrapper = ClepsSSHWrapper(wd=".", username=USERNAME, password=PASSWORD)
        wrapper.clone_repo(repo_url, dst_dir, git_branch)

        mock_env.assert_command_was_executed(HOSTNAME, 22, git_clone_cmd)
        mock_env.assert_command_was_executed(HOSTNAME, 22, git_checkout_cmd)

    mock_env.cleanup_environment()
