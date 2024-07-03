## Plex Backup and Restore Script ##
 
This script provides a simple and efficient way to backup and restore your Plex Media Server data on Windows systems. It supports various archive formats and allows you to exclude specific folders from the backup.

## Features ##

- Backs up Plex Media Server data and registry settings
- Supports multiple archive formats: zip, 7z, rar, tar.gz
- Allows excluding specific folders from the backup
- Handles stopping and starting Plex services
- Logs all operations for easy debugging

## Requirements ##

- Python 3.6+
- Windows 7, 8, 10, 11, or their server versions

## Dependencies ##

The script relies on the following Python libraries:

- `tqdm`
- `py7zr`
- `patool`
- `PyYAML`

Install the dependencies using the following command:

```
pip install -r requirements.txt
```

## Configuration ##
Create a new config.yaml file or rename the "config.sample.yaml" in the same directory as the script with the following structure:

```
backup_dir: "C:/Backups" # The directory where the backups will be stored
exclude_folders: # The folders to exclude from the backup
  - "Diagnostics"
  - "Crash Reports"
  - "Updates"
  - "Logs"
archive_format: "zip"  # Options: zip, 7z, rar, tar.gz
compression_level: 5   # Compression level: 0 (no compression) to 9 (maximum compression)
```

## Usage ##

To create a backup, run the script with the backup mode:
```
python plexbackup.py backup
```
To restore from a backup, run the script with the restore mode:
```
python plexbackup.py restore
```

## Command-line Arguments ##
Optional. Specifies the path to the configuration file. If not provided, the script looks for config.yaml in the same directory.
Example:
```python plexbackup.py backup --config C:/Path/To/config.yaml```

## Logging ##

The script logs all operations to the logs folder. Each run generates a new log file with a timestamp.

## Contributing ##

Feel free to submit issues or pull requests if you find any bugs or have feature requests.

## License ##

This project is licensed under the MIT License. See the LICENSE file for details.
