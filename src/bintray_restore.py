#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path

import requests
from src.bintray_client import BintrayClient
from src.bintray_client import get_sha1_hash
from src.bintray_client import PROGRESS_BAR_FORMAT
from progress.bar import IncrementalBar


def check_dirs_exist(repositories):
    for repository in repositories:
        path = Path(f"{repository}")
        if not path.exists():
            raise Exception(f"{path} does not exist.")


def get_local_files(repositories: list):
    package_metadata = []
    file_paths = []

    print(f"Discovering local files")
    for repo_name in repositories:
        for path in Path(repo_name).glob("**/*"):
            if path.is_file():
                if path.name == "package_metadata.json":
                    package_metadata.append(json.loads(path.read_text()))
                else:
                    file_paths.append(path)

    return file_paths, package_metadata


def create_new_packages(
    bintray_client, local_package_metadata, bintray_package_metadata
):
    created_packages = 0
    for package in IncrementalBar(
        f"Creating packages", suffix=PROGRESS_BAR_FORMAT
    ).iter(local_package_metadata):
        package_name = package["name"]
        if not any(
            bintray_metadata["name"] == package_name
            for bintray_metadata in bintray_package_metadata
        ):
            created_packages += 1
            bintray_client.create_package(package["repo"], package)
    print(
        f"created {created_packages} packages, skipped {len(local_package_metadata) - created_packages} packages that already existed"
    )


def local_path(bintray_file):
    return f"{bintray_file['repo']}/{bintray_file['package']}/{bintray_file['version']}/{bintray_file['path']}"


def upload_changed_files(bintray_client, local_files, bintray_files):
    uploaded_files = 0
    for path in IncrementalBar(f"Uploading files", suffix=PROGRESS_BAR_FORMAT).iter(
        local_files
    ):
        if not any(
            str(path) == local_path(bintray_file)
            and get_sha1_hash(path) == bintray_file["sha1"]
            for bintray_file in bintray_files
        ):
            uploaded_files += 1
            bintray_client.upload_file(path)
    print(
        f"uploaded {uploaded_files} files, skipped {len(local_files) - uploaded_files} files that already existed"
    )


def restore(username, token, organisation, repositories):
    check_dirs_exist(repositories)
    bintray_api_creds = requests.auth.HTTPBasicAuth(username, token)
    bintray_client = BintrayClient(organisation, api_creds=bintray_api_creds)

    local_files, local_package_metadata = get_local_files(repositories)
    bintray_files, bintray_package_metadata = bintray_client.get_metadata(repositories)

    create_new_packages(
        bintray_client, local_package_metadata, bintray_package_metadata
    )
    upload_changed_files(bintray_client, local_files, bintray_files)


if __name__ == "__main__":
    username = os.environ["BINTRAY_USERNAME"]
    token = os.environ["BINTRAY_TOKEN"]
    organisation = os.environ["BINTRAY_ORGANISATION"] # e.g. 'hmrc' or 'hmrc-digital'
    repositories = ["releases", "sbt-plugin-releases"]
    restore(username, token, organisation, repositories)
