import argparse
import os
import subprocess
import datetime
import shutil
import zipfile
import py7zr
import patoolib
import winreg
import logging
from tqdm import tqdm
import yaml

# Setup logging
def setup_logging():
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, f"plexbackup_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

# Read configuration file
def read_config(config_path):
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except yaml.YAMLError as e:
        logging.error(f"Error reading configuration file: {e}")
        raise ValueError(f"Error reading configuration file: {e}")
    except FileNotFoundError as e:
        logging.error(f"Configuration file not found: {e}")
        raise FileNotFoundError(f"Configuration file not found: {e}")

# Stop Plex services
def stop_plex_services():
    services = ["PlexUpdateService", "PlexService"]
    for service in services:
        try:
            logging.debug(f"Attempting to stop service: {service}")
            result = subprocess.run(["sc", "stop", service], check=True, capture_output=True, text=True)
            logging.info(f"Stopped service {service}: {result.stdout}")
        except subprocess.CalledProcessError as e:
            if "1060" in str(e):
                logging.info(f"Service {service} does not exist, skipping. Error: {e.stderr}")
            else:
                logging.warning(f"Error stopping service {service}: {e.stderr}")
    try:
        result = subprocess.run(["taskkill", "/F", "/IM", "Plex Media Server.exe"], check=True, capture_output=True, text=True)
        logging.info(f"Killed Plex Media Server process: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logging.warning(f"Error killing Plex Media Server process: {e.stderr}")

# Start Plex services
def start_plex_services():
    services = ["PlexUpdateService", "PlexService"]
    for service in services:
        try:
            logging.debug(f"Attempting to start service: {service}")
            result = subprocess.run(["sc", "start", service], check=True, capture_output=True, text=True)
            logging.info(f"Started service {service}: {result.stdout}")
        except subprocess.CalledProcessError as e:
            if "1060" in str(e):
                logging.info(f"Service {service} does not exist, skipping. Error: {e.stderr}")
            else:
                logging.warning(f"Error starting service {service}: {e.stderr}")

# Get Plex installation path from the registry
def get_plex_install_path():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Plex, Inc.\Plex Media Server") as key:
            install_path, _ = winreg.QueryValueEx(key, "InstallFolder")
            return install_path
    except FileNotFoundError:
        logging.error("Plex install path not found in registry.")
        raise FileNotFoundError("Plex install path not found in registry.")

# Backup Plex registry entries
def backup_registry(backup_zip):
    registry_backup_file = "plex_registry_backup.reg"
    subprocess.run(["reg", "export", r"HKEY_CURRENT_USER\SOFTWARE\Plex, Inc.\Plex Media Server", registry_backup_file], check=True)
    with zipfile.ZipFile(backup_zip, 'a') as zipf:
        zipf.write(registry_backup_file, arcname=registry_backup_file)
    os.remove(registry_backup_file)
    logging.info(f"Registry backed up to {backup_zip}")

# Compress directory to various archive formats
def compress_directory(src_dir, archive_path, format='zip', compression_level=5, exclude_folders=[]):
    total_files = sum([len(files) for r, d, files in os.walk(src_dir) if os.path.basename(r) not in exclude_folders])
    if format == 'zip':
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            with tqdm(total=total_files, desc="Compressing Backup") as pbar:
                for root, dirs, files in os.walk(src_dir):
                    dirs[:] = [d for d in dirs if d not in exclude_folders]
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, src_dir)
                        zipf.write(file_path, arcname, compress_type=zipfile.ZIP_DEFLATED, compresslevel=compression_level)
                        pbar.update(1)
    elif format == '7z':
        with py7zr.SevenZipFile(archive_path, 'w', filters=[{"id": py7zr.FILTER_LZMA2, "preset": compression_level}]) as archive:
            with tqdm(total=total_files, desc="Compressing Backup") as pbar:
                for root, dirs, files in os.walk(src_dir):
                    dirs[:] = [d for d in dirs if d not in exclude_folders]
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, src_dir)
                        archive.write(file_path, arcname)
                        pbar.update(1)
    else:
        temp_folder = os.path.join(os.path.dirname(archive_path), "temp_backup_folder")
        os.makedirs(temp_folder, exist_ok=True)
        shutil.copytree(src_dir, temp_folder, dirs_exist_ok=True)
        patoolib.create_archive(archive_path, (temp_folder,), verbosity=1)
        shutil.rmtree(temp_folder)
    logging.info(f"Compressed {src_dir} to {archive_path} in {format} format")

# Extract archive to destination directory
def extract_archive(archive_path, dest_dir, format='zip'):
    if format == 'zip':
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            total_files = len(zip_ref.namelist())
            with tqdm(total=total_files, desc="Extracting Backup") as pbar:
                for file in zip_ref.namelist():
                    zip_ref.extract(file, dest_dir)
                    pbar.update(1)
    elif format == '7z':
        with py7zr.SevenZipFile(archive_path, 'r') as archive:
            total_files = len(archive.getnames())
            with tqdm(total=total_files, desc="Extracting Backup") as pbar:
                archive.extractall(dest_dir)
                pbar.update(1)
    else:
        patoolib.extract_archive(archive_path, outdir=dest_dir, verbosity=1)
    logging.info(f"Extracted {archive_path} to {dest_dir} in {format} format")

# Restore Plex registry entries from backup
def restore_registry(backup_zip):
    with zipfile.ZipFile(backup_zip, 'r') as zipf:
        zipf.extract("plex_registry_backup.reg")
    subprocess.run(["reg", "import", "plex_registry_backup.reg"], check=True)
    os.remove("plex_registry_backup.reg")
    logging.info(f"Registry restored from {backup_zip}")

# Main function
def main(mode='backup', config_path=None):
    setup_logging()
    logging.info(f"Starting {mode} process")

    # Determine config file path
    if config_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'config.yaml')
        
    print(f"Using configuration file: {config_path}")
    logging.info(f"Using configuration file: {config_path}")

    # Read config file
    config = read_config(config_path)

    # Get configuration settings
    backup_dir = config.get('backup_dir', 'C:/Backups')
    exclude_folders = config.get('exclude_folders', ['Diagnostics', 'Crash Reports', 'Updates', 'Logs'])
    archive_format = config.get('archive_format', 'zip')
    compression_level = config.get('compression_level', 5)
    
    # Determine Plex data and install paths
    plex_data_path = os.path.join(os.environ['LOCALAPPDATA'], 'Plex Media Server')
    plex_install_path = get_plex_install_path()

    # Create timestamped archive file name
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    archive_path = os.path.join(backup_dir, f'plex_backup_{timestamp}.{archive_format}')

    # Perform backup or restore
    if mode == 'backup':
        stop_plex_services()
        
        compress_directory(plex_data_path, archive_path, format=archive_format, compression_level=compression_level, exclude_folders=exclude_folders)
        backup_registry(archive_path)
        
        start_plex_services()
        
        print("Backup process completed.")
        logging.info("Backup process completed.")
    elif mode == 'restore':
        latest_backup_archive = sorted([f for f in os.listdir(backup_dir) if f.endswith(f'.{archive_format}')])[-1]
        latest_backup_archive_path = os.path.join(backup_dir, latest_backup_archive)
        
        stop_plex_services()
        
        extract_archive(latest_backup_archive_path, plex_data_path, format=archive_format)
        restore_registry(latest_backup_archive_path)
        
        start_plex_services()
        
        print("Restore process completed.")
        logging.info("Restore process completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plex Backup and Restore Script')
    parser.add_argument('mode', choices=['backup', 'restore'], help='Mode to run the script in: backup or restore')
    parser.add_argument('--config', default=None, help='Path to the config file')

    args = parser.parse_args()
    main(args.mode, args.config)
