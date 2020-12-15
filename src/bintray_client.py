#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os

import requests
from progress.bar import IncrementalBar
from tenacity import retry

PROGRESS_BAR_FORMAT = "%(percent).1f%% - remaining %(remaining)d - eta %(eta)ds"


def get_sha1_hash(path):
    pathstr = str(path)
    stream = os.popen(f"sha1sum {pathstr}")
    return stream.read().split(" ")[0]


class BintrayClient:
    def __init__(self, organisation, api_creds):
        self.api_creds = api_creds
        self.organisation = organisation

    def get_repository_names(self):
        response = requests.get(
            f"https://bintray.com/api/v1/repos/{self.organisation}/",
            auth=self.api_creds,
        )
        response.raise_for_status()
        repository_names = map(lambda repository: repository["name"], response.json())
        return list(repository_names)

    def get_package_names(self, repository):
        discovered_packages = []
        packages_api = f"https://bintray.com/api/v1/repos/{self.organisation}/{repository}/packages?start_pos="
        start_pos = 0
        while True:
            print(f"getting package names: {start_pos}")
            response = requests.get(f"{packages_api}{start_pos}", auth=self.api_creds)
            response.raise_for_status()
            discovered_packages.extend([package["name"] for package in response.json()])
            # print(response.headers)
            if "X-RangeLimit-EndPos" not in response.headers:
                break
            if int(response.headers["X-RangeLimit-EndPos"]) + 1 == int(
                response.headers["X-RangeLimit-Total"]
            ):
                break
            start_pos = int(response.headers["X-RangeLimit-EndPos"]) + 1
        return discovered_packages

    def get_package_information(self, package_name, repository):
        response = requests.get(
            f"https://bintray.com/api/v1/packages/{self.organisation}/{repository}/{package_name}",
            auth=self.api_creds,
        )
        response.raise_for_status()
        return response.json()

    def write_package_metadata(self, package_information, file_path):
        with open(f"{file_path}/package_metadata.json", "w") as pm:
            json.dump(package_information, pm)

    def get_package_files(self, repository, package_name):
        files_response = requests.get(
            f"https://bintray.com/api/v1/packages/{self.organisation}/{repository}/{package_name}/files",
            auth=self.api_creds,
        )
        files_response.raise_for_status()
        return files_response.json()

    @retry
    def download_file(self, path, url):
        with requests.get(url, auth=self.api_creds) as r:
            r.raise_for_status()
            with path.open(mode="wb") as f:
                f.write(r.content)

    @retry
    def upload_file(self, path):
        response = requests.put(
            f"https://bintray.com/api/v1/content/{self.organisation}/{path}?publish=1&override=1",
            auth=self.api_creds,
            data=path.read_bytes(),
        )
        response.raise_for_status()

    def get_metadata(self, repositories):
        all_files = []
        package_metadata = []
        for repository in repositories:
            package_names = self.get_package_names(repository)
            for package in IncrementalBar(
                f"Downloading '{repository}' package information",
                suffix=PROGRESS_BAR_FORMAT,
            ).iter(package_names):
                package_metadata.append(
                    self.get_package_information(package, repository)
                )
                all_files.extend(self.get_package_files(repository, package))
        return all_files, package_metadata

    def create_package(self, repository, local_metadata):
        metadata = {
            "name": local_metadata["name"],
            "licenses": ["Apache-2.0"],
            "vcs_url": local_metadata.get("vcs_url", "https://github.com/hmrc"),
            "desc": local_metadata.get("desc"),
            "labels": local_metadata.get("labels"),
            "website_url": local_metadata.get("website_url"),
            "issue_tracker_url": local_metadata.get("issue_tracker_url"),
            "github_repo": local_metadata.get("github_repo"),
            "github_release_notes_file": local_metadata.get(
                "github_release_notes_file"
            ),
        }
        if metadata["vcs_url"] is None:
            metadata["vcs_url"] = "https://github.com/hmrc"
        package_response = requests.post(
            f"https://bintray.com/api/v1/packages/{self.organisation}/{repository}",
            auth=self.api_creds,
            json=metadata,
        )
        package_response.raise_for_status()
        return package_response.json()
