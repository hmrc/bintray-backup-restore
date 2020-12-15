
# bintray-backup-restore

These scripts perform a backup of a specified Bintray repo and restore to a specified Bintray repo.

They were created for the process of migrating the HMRC Bintray content from a paid account to a OSS account for B&D ticket PBD-2894.

They facilitated the download from an existing organisation (HMRC) and upload to a new organisation (HMRC-Digital).

### Install
You will need:
- python 3.8+
- poetry (https://python-poetry.org/docs/#installation)

To install necessary dependencies run:
```bash
poetry install
# to verify your install you can run the tests with
poetry run pytest
```

### Backup Script
The backup script uses environment vars to connect to a bintray organisation with suitable credentials to perform
incremental backups of the repositories that are specified in the script.  
Subsequent runs of the script will only download files where the file does not exists on local disk or the
sha1 hash does not match the one stored on Bintray.   
     
To use it you'll need to do the following:   
```bash
export BINTRAY_USERNAME="<your Bintray user>"
export BINTRAY_TOKEN="<your Bintray api token>"
export BINTRAY_ORGANISATION="<your source Bintray organisation name>"
poetry run python bintray_backup.py
```

### Restore Script
The restore script uses environment vars to connect to a bintray organisation with suitable credentials to perform
incremental restores to the repositories that are specified in the script.   
   
The restore process compares what is stored on disk and what is stored on the destination Bintray organisation
and will upload all files that are not present on Bintray. It also compares the sha1 hash of each file and
will upload to Bintray if the hashes do not match.   
      
To use it you'll need to do the following:   
```bash
export BINTRAY_USERNAME="<your Bintray user>"
export BINTRAY_TOKEN="<your Bintray api token>"
export BINTRAY_ORGANISATION="<your destination Bintray organisation name>"
poetry run python bintray_restore.py
```

###Tests
To run the tests, you will need to run:   
```
poetry install
poetry run pytest
```

### License

This code is open source software licensed under the [Apache 2.0 License]("http://www.apache.org/licenses/LICENSE-2.0.html").
