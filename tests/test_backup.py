# -*- coding: utf-8 -*-
import json
import re
import shutil
from pathlib import Path

from src.bintray_backup import backup, get_sha1_hash

import pytest
from httpretty import httpretty

TEST_REPO = "repo-to-test"


@pytest.fixture
def cleanup_directory():
    print("cleaning up")
    shutil.rmtree(TEST_REPO, ignore_errors=True)


def test_can_download_file():
    pass


def test_can_detect_file_changes():
    test_file = Path(f"/tmp/test_can_detect_file_changes")

    with test_file.open(mode="w") as pm:
        pm.write("1234567890")

    assert (
        get_sha1_hash(test_file)
        == "01b307acba4f54f55aafc33bb06bbbf6ca803e9a"
    )
    test_file.unlink()


def test_can_download_files(cleanup_directory):
    httpretty.enable(allow_net_connect=False)
    organisation = "hmrc"
    httpretty.reset()

    with_packages(organisation)
    with_package_metadata(organisation)
    with_package_file_metadata(organisation)
    with_files(organisation)

    backup("foo", "bar", organisation)

    assert Path(f"{TEST_REPO}/fake_package/package_metadata.json").exists()
    assert Path(f"{TEST_REPO}/fake_package_2/package_metadata.json").exists()
    assert Path(f"{TEST_REPO}/fake_package_3/package_metadata.json").exists()

    assert Path(
        f"{TEST_REPO}/fake_package/1.0.0/org/jfrog/powerutils/nutcracker/1.0.0/nutcracker-1.0.0-sources.jar"
    ).exists()
    assert (
        Path(
            f"{TEST_REPO}/fake_package/1.0.0/org/jfrog/powerutils/nutcracker/1.0.0/nutcracker-1.0.0-sources.jar"
        ).read_text()
        == "1234567890"
    )

    assert Path(
        f"{TEST_REPO}/fake_package_3/2.0.0/org/jfrog/powerutils/nutcracker/2.0.0"
    ).exists()


def test_detect_existing_files(cleanup_directory):
    httpretty.enable(allow_net_connect=False)
    organisation = "hmrc"
    httpretty.reset()

    with_packages(organisation)
    with_package_metadata(organisation)
    with_package_file_metadata(organisation)
    with_files(organisation)

    download_file_requests = 6
    total_requests = 14

    backup("foo", "bar", "hmrc")
    assert total_requests == len(httpretty.latest_requests)

    backup("foo", "bar", "hmrc")
    assert (total_requests * 2) - download_file_requests == len(
        httpretty.latest_requests
    ), "running a backup a second time should not redownload files"


def test_detect_changed_files(cleanup_directory):
    httpretty.enable(allow_net_connect=False)
    organisation = "hmrc"
    httpretty.reset()

    with_packages(organisation)
    with_package_metadata(organisation)
    with_package_file_metadata(organisation, changed_sha=True)
    with_files(organisation)

    total_requests = 14

    backup("foo", "bar", organisation)
    assert total_requests == len(httpretty.latest_requests)

    backup("foo", "bar", organisation)
    assert (total_requests * 2) == len(
        httpretty.latest_requests
    ), "running a backup a second time should redownload files if the sha has changed"


def with_files(organisation):
    httpretty.register_uri(
        httpretty.GET,
        re.compile(f"https://dl.bintray.com/{organisation}/.*"),
        status=200,
        body="1234567890",
    )


def with_package_file_metadata(organisation, changed_sha=False):
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/sbt-plugin-releases/fake_package/files",
        status=200,
        adding_headers={"Content-Type": "application/json"},
        body=json.dumps(
            [
                {
                    "name": "nutcracker-1.1-sources.jar",
                    "path": "org/jfrog/powerutils/nutcracker/1.0.0/nutcracker-1.0.0-sources.jar",
                    "package": "fake_package",
                    "version": "1.0.0",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 50,
                    "sha1": "01b307acba4f54f55aafc33bb06bbbf6ca803e9a"
                    if not changed_sha
                    else "something_else",
                },
                {
                    "name": "foo",
                    "path": "org/jfrog/powerutils/nutcracker/2.0.0/nutcracker-2.0.0-sources.jar",
                    "package": "fake_package",
                    "version": "2.0.0",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 65,
                    "sha1": "01b307acba4f54f55aafc33bb06bbbf6ca803e9a"
                    if not changed_sha
                    else "something_else",
                },
            ]
        ),
    )
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/sbt-plugin-releases/fake_package_2/files",
        status=200,
        adding_headers={"Content-Type": "application/json"},
        body=json.dumps(
            [
                {
                    "name": "nutcracker-1.1-sources.jar",
                    "path": "org/jfrog/powerutils/nutcracker/1.0.0/nutcracker-1.0.0-sources.jar",
                    "package": "fake_package_2",
                    "version": "1.0.0",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 50,
                    "sha1": "01b307acba4f54f55aafc33bb06bbbf6ca803e9a"
                    if not changed_sha
                    else "something_else",
                },
                {
                    "name": "foo",
                    "path": "org/jfrog/powerutils/nutcracker/2.0.0/nutcracker-2.0.0-sources.jar",
                    "package": "fake_package_2",
                    "version": "2.0.0",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 65,
                    "sha1": "01b307acba4f54f55aafc33bb06bbbf6ca803e9a"
                    if not changed_sha
                    else "something_else",
                },
            ]
        ),
    )
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/sbt-plugin-releases/fake_package_3/files",
        status=200,
        adding_headers={"Content-Type": "application/json"},
        body=json.dumps(
            [
                {
                    "name": "nutcracker-1.1-sources.jar",
                    "path": "org/jfrog/powerutils/nutcracker/1.0.0/nutcracker-1.0.0-sources.jar",
                    "package": "fake_package_3",
                    "version": "1.0.0",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 50,
                    "sha1": "01b307acba4f54f55aafc33bb06bbbf6ca803e9a"
                    if not changed_sha
                    else "something_else",
                },
                {
                    "name": "foo",
                    "path": "org/jfrog/powerutils/nutcracker/2.0.0/nutcracker-2.0.0-sources.jar",
                    "package": "fake_package_3",
                    "version": "2.0.0",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 65,
                    "sha1": "01b307acba4f54f55aafc33bb06bbbf6ca803e9a"
                    if not changed_sha
                    else "something_else",
                },
            ]
        ),
    )


def with_package_metadata(organisation):
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/sbt-plugin-releases/fake_package",
        status=200,
        adding_headers={
            "Content-Type": "application/json",
        },
        body=json.dumps({"name": "fake_package", "repo": TEST_REPO, "otherkey": 1}),
    )
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/sbt-plugin-releases/fake_package_2",
        status=200,
        adding_headers={
            "Content-Type": "application/json",
        },
        body=json.dumps({"name": "fake_package_2", "repo": TEST_REPO, "otherkey": 1}),
    )
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/sbt-plugin-releases/fake_package_3",
        status=200,
        adding_headers={
            "Content-Type": "application/json",
        },
        body=json.dumps({"name": "fake_package_3", "repo": TEST_REPO, "otherkey": 1}),
    )


def with_packages(organisation):
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/repos/{organisation}/sbt-plugin-releases/packages?start_pos=0",
        match_querystring=True,
        status=200,
        adding_headers={
            "Content-Type": "application/json",
            "X-RangeLimit-EndPos": "1",
            "X-RangeLimit-Total": "3",
        },
        body=json.dumps(
            [
                {"name": "fake_package", "linked": False},
                {"name": "fake_package_2", "linked": False},
            ]
        ),
    )
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/repos/{organisation}/sbt-plugin-releases/packages?start_pos=2",
        match_querystring=True,
        status=200,
        adding_headers={
            "Content-Type": "application/json",
            "X-RangeLimit-EndPos": "2",
            "X-RangeLimit-Total": "3",
        },
        body=json.dumps(
            [
                {"name": "fake_package_3", "linked": False},
            ]
        ),
    )
