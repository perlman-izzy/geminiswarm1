"""
File handling agent for reading and writing files safely
"""
import os
import shutil
from logger import setup_logger

logger = setup_logger("file_agent")

def read_file(path):
    """Read a file and return its contents as a string"""
    try:
        logger.debug(f"Reading file: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.debug(f"Successfully read {len(content)} bytes from {path}")
        return content
    except Exception as e:
        logger.error(f"Error reading file {path}: {str(e)}")
        raise

def write_file(path, content):
    """Write content to a file with backup"""
    try:
        # Create backup
        backup_path = f"{path}.bak"
        if os.path.exists(path):
            logger.debug(f"Creating backup of {path} to {backup_path}")
            shutil.copy2(path, backup_path)
        
        # Write new content
        logger.debug(f"Writing {len(content)} bytes to {path}")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.debug(f"Successfully wrote to {path}")
        return True
    except Exception as e:
        logger.error(f"Error writing to file {path}: {str(e)}")
        
        # Try to restore from backup if available
        if os.path.exists(backup_path):
            logger.info(f"Attempting to restore from backup {backup_path}")
            try:
                shutil.copy2(backup_path, path)
                logger.info(f"Restored {path} from backup")
            except Exception as restore_error:
                logger.error(f"Failed to restore from backup: {str(restore_error)}")
        
        raise