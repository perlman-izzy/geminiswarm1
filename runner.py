"""
Command runner module to safely execute shell commands 
and capture stdout/stderr
"""
import subprocess
import shlex
from typing import Union, Tuple, List
from logger import setup_logger

logger = setup_logger("runner")

def run_command(cmd: Union[str, List[str]]) -> Tuple[int, str, str]:
    """
    Run a shell command and return exit code, stdout, stderr.
    
    Args:
        cmd: Command to run as string or list of args
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    if isinstance(cmd, str):
        logger.debug(f"Running command: {cmd}")
        args = shlex.split(cmd)
    else:
        logger.debug(f"Running command: {' '.join(cmd)}")
        args = cmd
    
    try:
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate()
        return_code = process.returncode
        
        logger.debug(f"Command returned with code {return_code}")
        
        if return_code != 0:
            logger.warning(f"Command failed with return code {return_code}")
            if stderr:
                logger.debug(f"stderr: {stderr[:500]}" + ("..." if len(stderr) > 500 else ""))
        
        return return_code, stdout, stderr
    
    except Exception as e:
        logger.error(f"Error running command: {str(e)}")
        return 1, "", str(e)