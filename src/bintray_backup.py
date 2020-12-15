#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
from pathlib import Path

import requests
from progress.bar import IncrementalBar

from .bintray_client import BintrayClient
from .bintray_client import get_sha1_hash
from .bintray_client import PROGRESS_BAR_FORMAT


def backup(username, token, organisation):
    # repositories = ["releases", "sbt-plugin-releases"]
    repositories = ["sbt-plugin-releases"]
    bintray_api_creds = requests.auth.HTTPBasicAuth(username, token)
    bintray_client = BintrayClient(organisation, api_creds=bintray_api_creds)

    all_files, package_metadata = bintray_client.get_metadata(repositories)
    print(f"There are {len(all_files)} files")
    skipped_files = 0
    with IncrementalBar(
        "Downloading files", max=len(all_files), suffix=PROGRESS_BAR_FORMAT
    ) as bar:
        for index, file in enumerate(all_files, start=1):
            path = Path(
                f"{file['repo']}/{file['package']}/{file['version']}/{file['path']}"
            )
            if path.exists() and (get_sha1_hash(path) == file["sha1"]):
                skipped_files += 1
            else:
                # print(f"downloading {index}/{len(all_files)}")
                path.parent.mkdir(parents=True, exist_ok=True)
                bintray_client.download_file(
                    path,
                    f"https://dl.bintray.com/{organisation}/{file['repo']}/{file['path']}",
                )
            bar.next()
    print(f"Skipped {skipped_files} already downloaded files")

    print("Writing package_metadata")
    for package in package_metadata:
        path = Path(f"{package['repo']}/{package['name']}/package_metadata.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open(mode="w") as pm:
            json.dump(package, pm)

    print("Done!")


if __name__ == "__main__":
    username = os.environ["BINTRAY_USERNAME"]
    token = os.environ["BINTRAY_TOKEN"]
    organisation = os.environ["BINTRAY_ORGANISATION"] #e.g. 'hmrc' or 'hmrc-digital'
    backup(username, token, organisation)
