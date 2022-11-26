#!/usr/bin/env python3
"""Prompts the user and runs project setup during ``footing setup``"""
import os
import re
import subprocess
import sys

import requests


ORG_NAME = "{{ cookiecutter.org_name }}"
REPO_NAME = "{{ cookiecutter.repo_name }}"
MODULE_NAME = "{{ cookiecutter.module_name }}"
DESCRIPTION = "{{ cookiecutter.short_description }}"
PR = "{{ cookiecutter._pr }}"
FOOTING_ENV_VAR = "_FOOTING"
GITHUB_API_TOKEN_ENV_VAR = "GITHUB_API_TOKEN"


class Error(Exception):
    """Base exception for this script"""


class RemoteRepoExistsError(Error):
    """Thrown when a remote Github repo already exists"""


class GithubPushError(Error):
    """Thrown when there is an issue pushing to the remote repo"""


class CredentialsError(Error):
    """Thrown when the user does not have valid credentials to use template"""


def _shell(cmd, check=True, stdin=None, stdout=None, stderr=None):  # pragma: no cover
    """Runs a subprocess shell with check=True by default"""
    return subprocess.run(cmd, shell=True, check=check, stdin=stdin, stdout=stdout, stderr=stderr)


def get_user_input(prompt_text):
    return input(prompt_text).strip()


def yesno(message, default="yes", suffix=" "):
    """Prompt user to answer yes or no.

    Return True if the default is chosen, otherwise False.
    """
    if default == "yes":
        yesno_prompt = "[Y/n]"
    elif default == "no":
        yesno_prompt = "[y/N]"
    else:
        raise ValueError("default must be 'yes' or 'no'.")

    if message != "":
        prompt_text = f"{message} {yesno_prompt}{suffix}"
    else:
        prompt_text = f"{yesno_prompt}{suffix}"

    while True:
        response = get_user_input(prompt_text)
        if response == "":
            return True
        else:
            if re.match("^(y)(es)?$", response, re.IGNORECASE):
                if default == "yes":
                    return True
                else:
                    return False
            elif re.match("^(n)(o)?$", response, re.IGNORECASE):
                if default == "no":
                    return True
                else:
                    return False


class GithubClient:
    """Utility client for accessing Github API"""

    def __init__(self):
        self.api_token = os.environ[GITHUB_API_TOKEN_ENV_VAR]

    def _call_api(self, verb, url, check=True, **request_kwargs):
        """Perform a github API call

        Args:
            verb (str): Can be "post", "put", or "get"
            url (str): The base URL with a leading slash for Github API (v3)
        """
        api = "https://api.github.com{}".format(url)
        auth_headers = {"Authorization": "token {}".format(self.api_token)}
        headers = {**auth_headers, **request_kwargs.pop("headers", {})}
        resp = getattr(requests, verb)(api, headers=headers, **request_kwargs)
        if check:
            resp.raise_for_status()
        return resp

    def get(self, url, check=True, **request_kwargs):
        """Github API get"""
        return self._call_api("get", url, check=check, **request_kwargs)

    def post(self, url, check=True, **request_kwargs):
        """Github API post"""
        return self._call_api("post", url, check=check, **request_kwargs)

    def put(self, url, check=True, **request_kwargs):
        """Github API put"""
        return self._call_api("put", url, check=check, **request_kwargs)

    def patch(self, url, check=True, **request_kwargs):
        """Github API patch"""
        return self._call_api("patch", url, check=check, **request_kwargs)


def github_create_repo(
    repo_name,
    short_description,
    disable_squash_merge=True,
    disable_merge_commit=False,
    disable_rebase_merge=True,
    has_wiki=False,
    prompt=True,
):
    """Creates a remote github repo

    Args:
        repo_name (str): The github repository name
        short_description (str): A short description of the repository
        disable_squash_merge (bool, default=True): Disable squash merging of
            the repo
        disable_merge_commit (bool, default=False): Disable merge commit of
            the repo
        disable_rebase_merge (bool, default=True): Disable rebase merge of
            the repo
        has_wiki (bool, default=False): Disable wiki on repo.
        prompt (bool, default=True): Prompt the user to continue if any
            errors happen

    Raises:
        `RemoteRepoExistsError`: When the remote git repo already exists
    """
    github_client = GithubClient()

    user = github_client.get("/user")
    if user.json()["login"].lower() == ORG_NAME:
        repo_api = "/user/repos"
    else:
        repo_api = f"/orgs/{ORG_NAME}/repos"

    resp = github_client.post(
        repo_api,
        check=False,
        json={
            "name": repo_name,
            "description": short_description,
            "private": True,
            "has_wiki": has_wiki,
            "allow_squash_merge": not disable_squash_merge,
            "allow_merge_commit": not disable_merge_commit,
            "allow_rebase_merge": not disable_rebase_merge,
        },
    )

    repo_already_exists = resp.json().get("message") == "Repository creation failed."
    if resp.status_code == requests.codes.unprocessable and repo_already_exists:
        msg = (
            "Remote github repo already exists at"
            f" https://github.com/{ORG_NAME}/{repo_name}.git."
        )

        raise RemoteRepoExistsError(msg)
    elif resp.status_code != requests.codes.created:
        print(
            f'An error happened during git repo creation - "{resp.json()}"',
            file=sys.stderr,
        )
        resp.raise_for_status()


def github_setup_branch_protection(repo_name, branch, branch_protection):
    """Sets up branch protection for a repository

    Args:
        repo_name (str): The repository name
        branch (str): The branch to protect
        branch_protection (dict): A dictionary of parameters expected by
            the Github API. See
            developer.github.com/v3/repos/branches/#update-branch-protection
            for examples on the required input
    """
    github_client = GithubClient()
    protection_api = f"/repos/{ORG_NAME}/{repo_name}/branches/{branch}/protection"
    github_client.put(
        protection_api,
        json=branch_protection,
        headers={"Accept": "application/vnd.github.loki-preview+json"},
    )


def github_push_initial_repo(
    repo_name,
    initial_commit=["Initial scaffolding [skip ci]", "Type: trivial"],
    prompt=True,
):
    """Initializes local and remote Github repositories from a footing project

    Args:
        repo_name (str): The repository name
        initial_commit (str|List[str], optional): The initial commit message of
            the repo.
        prompt (bool, default=True): Prompt to continue on failure
    """
    api_token = os.environ[GITHUB_API_TOKEN_ENV_VAR]
    remote = f"https://{api_token}@github.com/{ORG_NAME}/{repo_name}.git"
    if isinstance(initial_commit, str):
        initial_commit = [initial_commit]

    _shell("git init")

    git_name = os.environ.get("GITHUB_NAME", "Name")
    git_email = os.environ.get("GITHUB_EMAIL", "email@email.com")
    _shell(f"git config user.name '{git_name}'")
    _shell(f"git config user.email '{git_email}'")
    _shell("git add .")
    _shell("git commit " + " ".join(f'-m "{msg}"' for msg in initial_commit))
    _shell("git branch -M main")
    _shell(f"git remote add origin {remote}")

    ret = _shell("git push origin main", check=False)
    if ret.returncode != 0:
        msg = "There was an error when pushing the initial repository."
        raise GithubPushError(msg)


def cleanup():
    # Cleanup extra files
    if not PR:
        os.remove(f"{MODULE_NAME}/hello.py")


def footing_setup():
    # Make sure requests is installed
    print("Installing requests library for repository setup...")
    _shell("pip3 install requests")

    print("Checking credentials.")
    if not os.getenv(GITHUB_API_TOKEN_ENV_VAR):
        raise CredentialsError(
            f'You must set a "{GITHUB_API_TOKEN_ENV_VAR}" environment variable'
            " with repo creation permissions in order to spin up a public"
            " python library project. Create a personal access token"
            " at https://github.com/settings/tokens"
        )

    print(
        f"Creating the github repository at https://github.com/{ORG_NAME}/{REPO_NAME}"
    )
    github_create_repo(REPO_NAME, DESCRIPTION)

    print("Creating initial repository and pushing to main.")
    github_push_initial_repo(REPO_NAME)

    # print("Setting up default branch protection.")
    # github_setup_branch_protection(
    #     REPO_NAME,
    #     "main",
    #     {
    #         "required_pull_request_reviews": None,
    #         "enforce_admins": False,
    #         "restrictions": None,
    #     },
    # )

    print(
        f'Setup complete! cd into "{REPO_NAME}", make a new branch,'
        ' and type "make setup" to set up your development environment.'
    )


if __name__ == "__main__":
    # Don't allow this template to be used by other tools like cookiecutter
    if not os.getenv(FOOTING_ENV_VAR):
        print(
            "This template can only be used with Footing for project spin up. "
            "Consult the footing docs at https://github.com/Opus10/footing"
        )
        sys.exit(1)

    cleanup()

    if os.getenv(FOOTING_ENV_VAR) == "setup":
        footing_setup()
