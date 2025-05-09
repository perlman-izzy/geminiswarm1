import argparse
import threading
from task_queue import TaskQueue
from loop_controller import fix_file_loop


def worker(queue, proxy_url, test_cmd, max_attempts):
    while True:
        path = queue.pop()
        if path is None:
            break
        print(f"[{threading.current_thread().name}] Processing {path}")
        success = fix_file_loop(path, proxy_url, test_cmd, max_attempts)
        print(f"[{threading.current_thread().name}] Finished {path}: {'Success' if success else 'Failure'}")


def main():
    parser = argparse.ArgumentParser(description="Gemini Swarm Debugger")
    parser.add_argument("action", choices=["fix"], help="Action to perform: fix")
    parser.add_argument("files", nargs="+", help="List of Python files to debug and fix")
    parser.add_argument("--proxy", default="http://localhost:3000", help="URL of the Gemini Flask proxy")
    parser.add_argument("--test-cmd", required=True, help="Command to test the file, e.g., 'pytest tests' or 'python script.py'")
    parser.add_argument("--attempts", type=int, default=3, help="Max fix attempts per file")
    parser.add_argument("--workers", type=int, default=2, help="Number of parallel worker threads")
    args = parser.parse_args()

    if args.action == "fix":
        queue = TaskQueue()
        for f in args.files:
            queue.push(f)
        # Push sentinel None for each worker to exit
        for _ in range(args.workers):
            queue.push(None)

        threads = []
        for i in range(args.workers):
            t = threading.Thread(
                target=worker,
                args=(queue, args.proxy, args.test_cmd, args.attempts),
                name=f"Worker-{i+1}"
            )
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
    else:
        parser.error("Unsupported action. Use 'fix'.")


if __name__ == "__main__":
    main()