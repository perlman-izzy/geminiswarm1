import sys
from file_agent import read_file, write_file
from runner import run_command
from gemini_client import propose_fix
from logger import setup_logger

logger = setup_logger("loop_controller")

def fix_file_loop(path, proxy_url, test_cmd, max_attempts=3):
    """
    Loop: read code, run test, if fail propose fix, write, retry.
    test_cmd can be a list or string for subprocess.
    """
    for attempt in range(1, max_attempts+1):
        logger.info(f"Attempt {attempt}/{max_attempts} for {path}")
        code = read_file(path)
        ret, out, err = run_command(test_cmd)
        if ret == 0:
            logger.info("Tests passed. No fix needed.")
            return True
        logger.error(f"Error on attempt {attempt}: {err}")
        fix = propose_fix(proxy_url, code, err)
        if not fix.strip():
            logger.warning("No fix proposed. Stopping.")
            return False
        try:
            write_file(path, fix)
            logger.info(f"Applied fix to {path}")
        except Exception as e:
            logger.error(f"Failed to write file {path}: {e}")
            return False
    logger.error("Reached max attempts without passing tests.")
    return False

if __name__ == '__main__':
    if len(sys.argv) < 4:
        logger.error("Usage: python loop_controller.py <script.py> <proxy_url> <test_command> [max_attempts]")
        sys.exit(1)
    script = sys.argv[1]
    proxy = sys.argv[2].rstrip('/')
    test = sys.argv[3]
    attempts = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    success = fix_file_loop(script, proxy, test, attempts)
    sys.exit(0 if success else 1)