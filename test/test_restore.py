# -*- coding: utf-8 -*-
import json
import re
import shutil
from pathlib import Path

import pytest
from httpretty import httpretty

from ..bintray_restore import get_local_files
from ..bintray_restore import restore

TEST_REPO = "repo-to-check"


@pytest.yield_fixture
def test_repo():
    create_local_package("fake_package")
    create_local_package("fake_package_2")
    create_local_package(
        "fake_package_3",
        extra_metadata={
            "desc": "a description",
            "labels": ["something"],
            "website_url": "example.com",
            "issue_tracker_url": "example.com",
            "github_repo": "hmrc/vat-registration",
            "github_release_notes_file": "README.md",
        },
    )
    create_local_package("fake_package_4", vcs_url=False)
    yield
    shutil.rmtree(TEST_REPO)


def create_local_package(package_name, vcs_url=True, extra_metadata=None):
    file = Path(f"{TEST_REPO}/{package_name}/0.0.1/this/is/my/path/foo.txt")
    file.parent.mkdir(parents=True)
    file.write_text("this is a test file")
    package_metadata = {
        "name": package_name,
        "repo": TEST_REPO,
    }
    if vcs_url:
        package_metadata["vcs_url"] = f"https://github.com/hmrc/{package_name}"
    if extra_metadata is not None:
        package_metadata.update(extra_metadata)
    Path(f"{TEST_REPO}/{package_name}/package_metadata.json").write_text(
        json.dumps(package_metadata)
    )


def test_discover_local_files(test_repo):
    file_paths, packages = get_local_files([TEST_REPO])

    assert file_paths == [
        Path(f"{TEST_REPO}/fake_package/0.0.1/this/is/my/path/foo.txt"),
        Path(f"{TEST_REPO}/fake_package_4/0.0.1/this/is/my/path/foo.txt"),
        Path(f"{TEST_REPO}/fake_package_2/0.0.1/this/is/my/path/foo.txt"),
        Path(f"{TEST_REPO}/fake_package_3/0.0.1/this/is/my/path/foo.txt"),
    ]
    assert packages == [
        {
            "name": "fake_package",
            "repo": "repo-to-check",
            "vcs_url": "https://github.com/hmrc/fake_package",
        },
        {"name": "fake_package_4", "repo": "repo-to-check"},
        {
            "name": "fake_package_2",
            "repo": "repo-to-check",
            "vcs_url": "https://github.com/hmrc/fake_package_2",
        },
        {
            "name": "fake_package_3",
            "repo": "repo-to-check",
            "vcs_url": "https://github.com/hmrc/fake_package_3",
            "desc": "a description",
            "labels": ["something"],
            "website_url": "example.com",
            "issue_tracker_url": "example.com",
            "github_repo": "hmrc/vat-registration",
            "github_release_notes_file": "README.md",
        },
    ]


def test_restores_files(test_repo):
    organisation = "hmrc-digital"
    httpretty.enable(allow_net_connect=False)
    httpretty.reset()

    with_packages(organisation)
    with_package_metadata(organisation)
    with_package_file_metadata(organisation)
    with_create_packages(organisation)
    with_file_upload(organisation)

    restore(
        username="hdjisand",
        token="hdiasjnhd",
        organisation=organisation,
        repositories=[TEST_REPO],
    )

    assert len(package_created_requests(httpretty, organisation)) == 2
    assert_package_created(
        httpretty,
        organisation,
        {
            "name": "fake_package_3",
            "licenses": ["Apache-2.0"],
            "vcs_url": "https://github.com/hmrc/fake_package_3",
            "desc": "a description",
            "labels": ["something"],
            "website_url": "example.com",
            "issue_tracker_url": "example.com",
            "github_repo": "hmrc/vat-registration",
            "github_release_notes_file": "README.md",
        },
    )
    assert_package_created(
        httpretty,
        organisation,
        {
            "name": "fake_package_4",
            "licenses": ["Apache-2.0"],
            "vcs_url": "https://github.com/hmrc",
            "desc": None,
            "labels": None,
            "website_url": None,
            "issue_tracker_url": None,
            "github_repo": None,
            "github_release_notes_file": None,
        },
    )
    uploads = file_uploaded_requests(httpretty)
    assert len(uploads) == 3
    assert (
        uploads[0].path
        == "/api/v1/content/hmrc-digital/repo-to-check/fake_package_4/0.0.1/this/is/my/path/foo.txt?publish=1&override=1"
    )
    assert uploads[0].body == b"this is a test file"
    assert (
        uploads[1].path
        == "/api/v1/content/hmrc-digital/repo-to-check/fake_package_2/0.0.1/this/is/my/path/foo.txt?publish=1&override=1"
    )
    assert uploads[1].body == b"this is a test file"


def test_that_upload_fails_when_no_local_files_exist():
    organisation = "hmrc-digital"
    httpretty.enable(allow_net_connect=False)

    with_packages(organisation)
    with_package_metadata(organisation)
    with_package_file_metadata(organisation)

    with pytest.raises(Exception):
        restore(
            username="hdjisand",
            token="hdiasjnhd",
            organisation=organisation,
            repositories=[TEST_REPO],
        )


def assert_package_created(httpretty, organisation, package_metadata):
    packages_created = package_created_requests(httpretty, organisation)
    assert len(packages_created) > 0
    assert request_made(packages_created, package_metadata)


def file_uploaded_requests(httpretty):
    return list(
        filter(
            lambda x: "/api/v1/content/" in x.path and x.method == httpretty.PUT,
            httpretty.latest_requests,
        )
    )


def package_created_requests(httpretty, organisation):
    return list(
        filter(
            lambda x: x.path == f"/api/v1/packages/{organisation}/{TEST_REPO}"
            and x.method == httpretty.POST,
            httpretty.latest_requests,
        )
    )


def request_made(requests, package_metadata):
    for request in requests:
        if json.loads(request.body) == package_metadata:
            return True
    return False


def with_file_upload(organisation):
    httpretty.register_uri(
        httpretty.PUT,
        re.compile(
            f"https://bintray.com/api/v1/content/{organisation}/{TEST_REPO}/.*"
        ),  # ?publish=1&override=1
        status=200,
        body="{}",
    )


def with_package_file_metadata(organisation):
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/{TEST_REPO}/fake_package/files",
        status=200,
        adding_headers={"Content-Type": "application/json"},
        body=json.dumps(
            [
                {
                    "name": "foo.txt",
                    "path": "this/is/my/path/foo.txt",
                    "package": "fake_package",
                    "version": "0.0.1",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 50,
                    "sha1": "5d03965084a5db13c178cbb1ffc120b360353685",
                },
                {
                    "name": "foo",
                    "path": "org/jfrog/powerutils/nutcracker/2.0.0/nutcracker-2.0.0-sources.jar",
                    "package": "fake_package",
                    "version": "0.0.1",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 65,
                    "sha1": "01b307acba4f54f55aafc33bb06bbbf6ca803e9a",
                },
            ]
        ),
    )
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/{TEST_REPO}/fake_package_2/files",
        status=200,
        adding_headers={"Content-Type": "application/json"},
        body=json.dumps(
            [
                {
                    "name": "foo.txt",
                    "path": "this/is/my/path/foo.txt",
                    "package": "fake_package_2",
                    "version": "0.0.1",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 50,
                    "sha1": "thisisthewronghash",
                },
                {
                    "name": "foo",
                    "path": "org/jfrog/powerutils/nutcracker/2.0.0/nutcracker-2.0.0-sources.jar",
                    "package": "fake_package_2",
                    "version": "0.0.1",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 65,
                    "sha1": "01b307acba4f54f55aafc33bb06bbbf6ca803e9a",
                },
            ]
        ),
    ),
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/{TEST_REPO}/fake_package_3/files",
        status=200,
        adding_headers={"Content-Type": "application/json"},
        body=json.dumps(
            [
                {
                    "name": "foo.txt",
                    "path": "this/is/my/path/foo.txt",
                    "package": "fake_package_2",
                    "version": "0.0.1",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 50,
                    "sha1": "5d03965084a5db13c178cbb1ffc120b360353685",
                }
            ]
        ),
    )
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/{TEST_REPO}/fake_package_666/files",
        status=200,
        adding_headers={"Content-Type": "application/json"},
        body=json.dumps(
            [
                {
                    "name": "foo.txt",
                    "path": "/this/is/my/path/foo.txt",
                    "package": "fake_package_666",
                    "version": "0.0.1",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 50,
                    "sha1": "5d03965084a5db13c178cbb1ffc120b360353685",
                },
                {
                    "name": "foo",
                    "path": "org/jfrog/powerutils/nutcracker/2.0.0/nutcracker-2.0.0-sources.jar",
                    "package": "fake_package_666",
                    "version": "0.0.1",
                    "repo": TEST_REPO,
                    "owner": "jfrog",
                    "created": "ISO8601 (yyyy-MM-dd'T'HH:mm:ss.SSSZ)",
                    "size": 65,
                    "sha1": "01b307acba4f54f55aafc33bb06bbbf6ca803e9a",
                },
            ]
        ),
    )


def with_package_metadata(organisation):
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/{TEST_REPO}/fake_package",
        status=200,
        adding_headers={
            "Content-Type": "application/json",
        },
        body=json.dumps({"name": "fake_package", "repo": TEST_REPO, "otherkey": 1}),
    )
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/{TEST_REPO}/fake_package_2",
        status=200,
        adding_headers={
            "Content-Type": "application/json",
        },
        body=json.dumps({"name": "fake_package_2", "repo": TEST_REPO, "otherkey": 1}),
    )
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/packages/{organisation}/{TEST_REPO}/fake_package_666",
        status=200,
        adding_headers={
            "Content-Type": "application/json",
        },
        body=json.dumps({"name": "fake_package_666", "repo": TEST_REPO, "otherkey": 1}),
    )


def with_packages(organisation):
    httpretty.register_uri(
        httpretty.GET,
        f"https://bintray.com/api/v1/repos/{organisation}/{TEST_REPO}/packages?start_pos=0",
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
        f"https://bintray.com/api/v1/repos/{organisation}/{TEST_REPO}/packages?start_pos=2",
        match_querystring=True,
        status=200,
        adding_headers={
            "Content-Type": "application/json",
            "X-RangeLimit-EndPos": "2",
            "X-RangeLimit-Total": "3",
        },
        body=json.dumps(
            [
                {
                    "name": "fake_package_666",
                    "linked": False,
                }  # this package should not exist localy
            ]
        ),
    )


def with_create_packages(organisation):
    httpretty.register_uri(
        httpretty.POST,
        f"https://bintray.com/api/v1/packages/{organisation}/{TEST_REPO}",
        status=201,
        adding_headers={
            "Content-Type": "application/json",
        },
        body=json.dumps({}),
    )
