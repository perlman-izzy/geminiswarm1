#!/usr/bin/env python3
"""
Enhanced Swarm Controller for multi-agent Gemini coordination.
This controller manages a swarm of agents that can:
1. Debug and fix code issues (using fix_file_loop)
2. Perform web searches and gather information
3. Process text from various sources
4. Execute system commands and scripts

The controller uses a priority-based delegation system where complex tasks
are routed to more powerful models and simple tasks to faster, more efficient models.
"""
import os
import sys
import time
import argparse
import threading
import queue
import logging
import json
import requests
import importlib
import subprocess
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Callable

# Import our modules
from task_queue import TaskQueue
from loop_controller import fix_file_loop
from gemini_client import call_gemini, web_search, fetch_url, scrape_text
from file_agent import read_file, write_file
from runner import run_command
from logger import setup_logger
from config import (
    PROXY_URL, LOG_DIR, WORKER_COUNT, MAX_ATTEMPTS,
    MAIN_PROXY_PORT, EXTENDED_PROXY_PORT
)

# Setup logging
logger = setup_logger("swarm_controller", log_dir=LOG_DIR)

# Define task priorities
class TaskPriority(Enum):
    LOW = "low"     # Simple tasks, use faster model
    HIGH = "high"   # Complex reasoning tasks, use more powerful model

# Define task types
class TaskType(Enum):
    PROMPT = "prompt"          # Simple prompt to AI
    CODE_FIX = "code_fix"      # Code debugging/fixing
    WEB_SEARCH = "web_search"  # Search the web
    WEB_FETCH = "web_fetch"    # Fetch URL content
    SCRAPE = "scrape"          # Scrape content from web
    READ_FILE = "read_file"    # Read a file
    WRITE_FILE = "write_file"  # Write to a file
    EXECUTE = "execute"        # Execute a command
    INSTALL_PACKAGE = "install_package"  # Install a Python package

class Task:
    """Represents a task to be processed by an agent in the swarm."""
    
    def __init__(
        self,
        task_type: TaskType,
        data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.LOW,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.task_type = task_type
        self.data = data
        self.priority = priority
        self.callback = callback
        self.id = f"{task_type.value}_{int(time.time() * 1000)}"
        self.result = None
        self.error = None
        self.completed = False
    
    def mark_completed(self, result=None, error=None):
        """Mark this task as completed with an optional result or error."""
        self.result = result
        self.error = error
        self.completed = True
        
        if self.callback and callable(self.callback):
            response = {
                "task_id": self.id,
                "task_type": self.task_type.value,
                "completed": self.completed,
                "result": self.result,
                "error": self.error
            }
            self.callback(response)
    
    def __str__(self):
        return f"Task(id={self.id}, type={self.task_type.value}, priority={self.priority.value})"

class SwarmController:
    """
    Controls a swarm of Gemini agents working on various tasks.
    Routes tasks to appropriate agents based on priority and type.
    """
    
    def __init__(
        self,
        main_proxy_url: str = f"http://localhost:{MAIN_PROXY_PORT}/gemini",
        extended_proxy_url: str = f"http://localhost:{EXTENDED_PROXY_PORT}/gemini",
        worker_count: int = WORKER_COUNT,
        max_attempts: int = MAX_ATTEMPTS
    ):
        self.main_proxy_url = main_proxy_url
        self.extended_proxy_url = extended_proxy_url
        self.worker_count = worker_count
        self.max_attempts = max_attempts
        
        # Task queues
        self.high_priority_queue = queue.Queue()
        self.low_priority_queue = queue.Queue()
        
        # Track tasks
        self.tasks = {}  # task_id -> Task object
        self.task_lock = threading.Lock()
        
        # Worker threads
        self.workers = []
        self.running = False
    
    def start(self):
        """Start the worker threads."""
        if self.running:
            logger.warning("Swarm already running")
            return
        
        self.running = True
        
        # Create and start worker threads
        for i in range(self.worker_count):
            t = threading.Thread(
                target=self._worker_loop,
                name=f"SwarmWorker-{i+1}",
                daemon=True
            )
            self.workers.append(t)
            t.start()
            logger.info(f"Started worker thread: {t.name}")
        
        logger.info(f"Swarm controller started with {self.worker_count} workers")
    
    def stop(self):
        """Stop all worker threads."""
        if not self.running:
            logger.warning("Swarm not running")
            return
        
        self.running = False
        
        # Add termination signals to the queues
        for _ in range(self.worker_count):
            self.high_priority_queue.put(None)
            self.low_priority_queue.put(None)
        
        # Wait for workers to finish
        for t in self.workers:
            if t.is_alive():
                t.join(timeout=2.0)
        
        self.workers = []
        logger.info("Swarm controller stopped")
    
    def add_task(self, task: Task) -> str:
        """
        Add a task to the appropriate queue based on its priority.
        Returns the task ID.
        """
        with self.task_lock:
            self.tasks[task.id] = task
        
        if task.priority == TaskPriority.HIGH:
            self.high_priority_queue.put(task)
            logger.info(f"Added high priority task: {task}")
        else:
            self.low_priority_queue.put(task)
            logger.info(f"Added low priority task: {task}")
        
        return task.id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task by its ID."""
        with self.task_lock:
            task = self.tasks.get(task_id)
            if not task:
                return {"error": f"Task {task_id} not found"}
            
            return {
                "task_id": task.id,
                "task_type": task.task_type.value,
                "priority": task.priority.value,
                "completed": task.completed,
                "result": task.result,
                "error": task.error
            }
    
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Wait for a task to complete and return its result."""
        start_time = time.time()
        while timeout is None or (time.time() - start_time) < timeout:
            status = self.get_task_status(task_id)
            if status.get("completed", False) or "error" in status:
                return status
            time.sleep(0.1)
        
        return {"error": f"Task {task_id} timed out"}
    
    def _worker_loop(self):
        """Main worker loop that processes tasks from the queues."""
        thread_name = threading.current_thread().name
        logger.info(f"{thread_name} starting")
        
        while self.running:
            # Check high priority queue first (with timeout)
            try:
                task = self.high_priority_queue.get(block=True, timeout=0.1)
                if task is None:  # Termination signal
                    logger.info(f"{thread_name} received termination signal")
                    break
                logger.info(f"{thread_name} processing high priority task: {task}")
                self._process_task(task, priority=TaskPriority.HIGH)
                self.high_priority_queue.task_done()
                continue
            except queue.Empty:
                pass  # No high priority tasks, check low priority
            
            # Check low priority queue
            try:
                task = self.low_priority_queue.get(block=True, timeout=0.5)
                if task is None:  # Termination signal
                    logger.info(f"{thread_name} received termination signal")
                    break
                logger.info(f"{thread_name} processing low priority task: {task}")
                self._process_task(task, priority=TaskPriority.LOW)
                self.low_priority_queue.task_done()
            except queue.Empty:
                continue  # No tasks available, loop again
        
        logger.info(f"{thread_name} exiting")
    
    def _process_task(self, task: Task, priority: TaskPriority):
        """Process a task based on its type and priority."""
        try:
            if task.task_type == TaskType.PROMPT:
                self._handle_prompt_task(task, priority)
            elif task.task_type == TaskType.CODE_FIX:
                self._handle_code_fix_task(task)
            elif task.task_type == TaskType.WEB_SEARCH:
                self._handle_web_search_task(task)
            elif task.task_type == TaskType.WEB_FETCH:
                self._handle_web_fetch_task(task)
            elif task.task_type == TaskType.SCRAPE:
                self._handle_scrape_task(task)
            elif task.task_type == TaskType.READ_FILE:
                self._handle_read_file_task(task)
            elif task.task_type == TaskType.WRITE_FILE:
                self._handle_write_file_task(task)
            elif task.task_type == TaskType.EXECUTE:
                self._handle_execute_task(task)
            elif task.task_type == TaskType.INSTALL_PACKAGE:
                self._handle_install_package_task(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
        except Exception as e:
            logger.exception(f"Error processing task {task.id}: {e}")
            task.mark_completed(error=str(e))
    
    def _handle_prompt_task(self, task: Task, priority: TaskPriority):
        """Handle a simple prompt to Gemini."""
        prompt = task.data.get("prompt", "")
        verbose = task.data.get("verbose", True)  # Default to verbose mode
        
        if not prompt:
            logger.error("Empty prompt provided to _handle_prompt_task")
            task.mark_completed(error="Empty prompt")
            return
        
        # Log the thinking process
        if verbose:
            logger.info(f"🧠 THINKING: Analyzing prompt complexity and selecting appropriate model...")
            logger.info(f"🧠 PROMPT: '{prompt[:100]}...' (truncated)")
            logger.info(f"🧠 PRIORITY: {priority.value}")
        
        # Choose proxy based on priority
        proxy_url = self.extended_proxy_url if priority == TaskPriority.HIGH else self.main_proxy_url
        
        if verbose:
            model_type = "LARGE (complex reasoning)" if priority == TaskPriority.HIGH else "SMALL (faster response)"
            logger.info(f"🧠 MODEL SELECTION: Using {model_type} model for this task")
            logger.info(f"🧠 ENDPOINT: Routing to {proxy_url}")
        
        # Add priority parameter for the extended proxy
        if proxy_url == self.extended_proxy_url:
            # Call extended proxy with priority parameter
            try:
                if verbose:
                    logger.info(f"🧠 ACTION: Sending prompt to extended proxy with priority={priority.value}")
                
                response = requests.post(
                    proxy_url,
                    json={"prompt": prompt, "priority": priority.value, "verbose": verbose}
                )
                response.raise_for_status()
                result = response.json()
                
                if verbose:
                    logger.info(f"🧠 RESPONSE: Successfully received response from extended proxy")
                    model_used = result.get("model_used", "unknown")
                    logger.info(f"🧠 MODEL USED: {model_used}")
                    
                    # Show a snippet of the response
                    response_text = result.get("response", "")
                    if response_text:
                        preview = response_text[:100] + "..." if len(response_text) > 100 else response_text
                        logger.info(f"🧠 RESPONSE PREVIEW: {preview}")
                
                task.mark_completed(result=result)
            except Exception as e:
                logger.error(f"ERROR in extended proxy call: {str(e)}", exc_info=True)
                task.mark_completed(error=f"Error calling extended proxy: {str(e)}")
        else:
            # Call main proxy
            try:
                if verbose:
                    logger.info(f"🧠 ACTION: Sending prompt to main proxy")
                
                result = call_gemini(proxy_url, prompt)
                
                if verbose:
                    logger.info(f"🧠 RESPONSE: Successfully received response from main proxy")
                    # Show a snippet of the response
                    preview = result[:100] + "..." if len(result) > 100 else result
                    logger.info(f"🧠 RESPONSE PREVIEW: {preview}")
                
                task.mark_completed(result={"response": result})
            except Exception as e:
                logger.error(f"ERROR in main proxy call: {str(e)}", exc_info=True)
                task.mark_completed(error=f"Error calling Gemini: {str(e)}")
    
    def _handle_code_fix_task(self, task: Task):
        """Handle a code fix task using the loop controller."""
        path = task.data.get("path", "")
        test_cmd = task.data.get("test_cmd", "")
        max_attempts = task.data.get("max_attempts", self.max_attempts)
        
        if not path or not test_cmd:
            task.mark_completed(error="Missing path or test_cmd")
            return
        
        try:
            success = fix_file_loop(path, self.main_proxy_url, test_cmd, max_attempts)
            task.mark_completed(result={"success": success})
        except Exception as e:
            task.mark_completed(error=f"Error fixing code: {str(e)}")
    
    def _handle_web_search_task(self, task: Task):
        """Handle a web search task."""
        query = task.data.get("query", "")
        max_results = task.data.get("max_results", 20)
        
        if not query:
            task.mark_completed(error="Missing query")
            return
        
        try:
            results = web_search(self.main_proxy_url, query, max_results)
            task.mark_completed(result={"results": results})
        except Exception as e:
            task.mark_completed(error=f"Error searching web: {str(e)}")
    
    def _handle_web_fetch_task(self, task: Task):
        """Handle a web fetch task."""
        url = task.data.get("url", "")
        
        if not url:
            task.mark_completed(error="Missing URL")
            return
        
        try:
            content = fetch_url(self.main_proxy_url, url)
            task.mark_completed(result={"content": content})
        except Exception as e:
            task.mark_completed(error=f"Error fetching URL: {str(e)}")
    
    def _handle_scrape_task(self, task: Task):
        """Handle a web scrape task."""
        url = task.data.get("url", "")
        selector = task.data.get("selector", None)
        
        if not url:
            task.mark_completed(error="Missing URL")
            return
        
        try:
            text = scrape_text(self.main_proxy_url, url, selector)
            task.mark_completed(result={"text": text})
        except Exception as e:
            task.mark_completed(error=f"Error scraping URL: {str(e)}")
    
    def _handle_read_file_task(self, task: Task):
        """Handle a read file task."""
        path = task.data.get("path", "")
        
        if not path:
            task.mark_completed(error="Missing path")
            return
        
        try:
            content = read_file(path)
            task.mark_completed(result={"content": content})
        except Exception as e:
            task.mark_completed(error=f"Error reading file: {str(e)}")
    
    def _handle_write_file_task(self, task: Task):
        """Handle a write file task."""
        path = task.data.get("path", "")
        content = task.data.get("content", "")
        
        if not path:
            task.mark_completed(error="Missing path")
            return
        
        try:
            write_file(path, content)
            task.mark_completed(result={"success": True})
        except Exception as e:
            task.mark_completed(error=f"Error writing file: {str(e)}")
    
    def _handle_execute_task(self, task: Task):
        """Handle an execute command task."""
        cmd = task.data.get("cmd", "")
        verbose = task.data.get("verbose", True)
        
        if not cmd:
            task.mark_completed(error="Missing command")
            return
        
        if verbose:
            logger.info(f"🧠 EXECUTING: Running shell command: {cmd}")
            
        try:
            returncode, stdout, stderr = run_command(cmd)
            
            if verbose:
                logger.info(f"🧠 EXECUTION COMPLETE: Command returned code {returncode}")
                if stdout:
                    logger.info(f"🧠 STDOUT: {stdout[:200]}..." if len(stdout) > 200 else f"🧠 STDOUT: {stdout}")
                if stderr:
                    logger.info(f"🧠 STDERR: {stderr[:200]}..." if len(stderr) > 200 else f"🧠 STDERR: {stderr}")
                    
            task.mark_completed(result={
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr
            })
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}", exc_info=True)
            task.mark_completed(error=f"Error executing command: {str(e)}")
            
    def _handle_install_package_task(self, task: Task):
        """Handle a Python package installation task."""
        package_name = task.data.get("package_name", "")
        version = task.data.get("version", "")
        upgrade = task.data.get("upgrade", False)
        verbose = task.data.get("verbose", True)
        
        if not package_name:
            task.mark_completed(error="Missing package name")
            return
        
        if verbose:
            logger.info(f"🧠 PACKAGE INSTALLATION: Preparing to install {package_name}" + 
                       (f" version {version}" if version else "") +
                       (" with upgrade" if upgrade else ""))
        
        try:
            # Build pip install command
            cmd = [sys.executable, "-m", "pip", "install"]
            
            if upgrade:
                cmd.append("--upgrade")
                
            if version:
                cmd.append(f"{package_name}=={version}")
            else:
                cmd.append(package_name)
                
            if verbose:
                logger.info(f"🧠 EXECUTING: {' '.join(cmd)}")
                
            # Run pip command
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if process.returncode == 0:
                if verbose:
                    logger.info(f"🧠 SUCCESS: Package {package_name} installed successfully")
                    
                # Try to import the newly installed package
                try:
                    # Convert from package_name to module_name (e.g., "package-name" to "package_name")
                    module_name = package_name.replace("-", "_")
                    importlib.import_module(module_name)
                    if verbose:
                        logger.info(f"🧠 VERIFICATION: Successfully imported {module_name}")
                except ImportError as ie:
                    if verbose:
                        logger.warning(f"🧠 NOTICE: Package installed but import failed: {str(ie)}")
                        logger.info("🧠 HINT: Package may use a different module name than the package name")
                        
                task.mark_completed(result={
                    "success": True,
                    "package": package_name,
                    "stdout": process.stdout,
                    "stderr": process.stderr
                })
            else:
                if verbose:
                    logger.error(f"🧠 ERROR: Failed to install {package_name}")
                    logger.error(f"🧠 PIP OUTPUT: {process.stderr}")
                    
                task.mark_completed(result={
                    "success": False,
                    "package": package_name,
                    "stdout": process.stdout,
                    "stderr": process.stderr
                })
        except Exception as e:
            logger.exception(f"Error installing package {package_name}: {str(e)}")
            task.mark_completed(error=f"Error installing package: {str(e)}")

def task_callback(response: Dict[str, Any]):
    """Example callback function to handle task completion."""
    logger.info(f"Task callback received: {response}")

def main():
    """Main function to run the swarm controller from the command line."""
    parser = argparse.ArgumentParser(description="Gemini Swarm Controller")
    parser.add_argument("--main-proxy", default=f"http://localhost:{MAIN_PROXY_PORT}/gemini", 
                        help="URL of the main Gemini proxy")
    parser.add_argument("--extended-proxy", default=f"http://localhost:{EXTENDED_PROXY_PORT}/gemini", 
                        help="URL of the extended Gemini proxy")
    parser.add_argument("--workers", type=int, default=WORKER_COUNT, 
                        help="Number of worker threads")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Prompt command
    prompt_parser = subparsers.add_parser("prompt", help="Send a prompt to Gemini")
    prompt_parser.add_argument("prompt", help="Prompt text")
    prompt_parser.add_argument("--priority", choices=["low", "high"], default="low", 
                              help="Task priority")
    
    # Code fix command
    fix_parser = subparsers.add_parser("fix", help="Fix code issues")
    fix_parser.add_argument("path", help="Path to the code file")
    fix_parser.add_argument("test_cmd", help="Command to test the code")
    fix_parser.add_argument("--attempts", type=int, default=MAX_ATTEMPTS, 
                           help="Maximum fix attempts")
    
    # Web search command
    search_parser = subparsers.add_parser("search", help="Search the web")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--max-results", type=int, default=20, 
                              help="Maximum number of search results")
    
    args = parser.parse_args()
    
    # Create and start the swarm controller
    controller = SwarmController(
        main_proxy_url=args.main_proxy,
        extended_proxy_url=args.extended_proxy,
        worker_count=args.workers
    )
    controller.start()
    
    try:
        if args.command == "prompt":
            priority = TaskPriority.HIGH if args.priority == "high" else TaskPriority.LOW
            task = Task(
                task_type=TaskType.PROMPT,
                data={"prompt": args.prompt},
                priority=priority,
                callback=task_callback
            )
            task_id = controller.add_task(task)
            logger.info(f"Added prompt task with ID: {task_id}")
            
            # Wait for the task to complete
            result = controller.wait_for_task(task_id)
            if "error" in result:
                logger.error(f"Task error: {result['error']}")
                return 1
            
            response = result.get("result", {}).get("response", "")
            print("Response:", response)
            
        elif args.command == "fix":
            task = Task(
                task_type=TaskType.CODE_FIX,
                data={
                    "path": args.path,
                    "test_cmd": args.test_cmd,
                    "max_attempts": args.attempts
                },
                priority=TaskPriority.HIGH,
                callback=task_callback
            )
            task_id = controller.add_task(task)
            logger.info(f"Added code fix task with ID: {task_id}")
            
            # Wait for the task to complete
            result = controller.wait_for_task(task_id)
            if "error" in result:
                logger.error(f"Task error: {result['error']}")
                return 1
            
            success = result.get("result", {}).get("success", False)
            if success:
                logger.info("Code fix successful")
            else:
                logger.warning("Code fix failed")
                return 1
            
        elif args.command == "search":
            task = Task(
                task_type=TaskType.WEB_SEARCH,
                data={
                    "query": args.query,
                    "max_results": args.max_results
                },
                priority=TaskPriority.LOW,
                callback=task_callback
            )
            task_id = controller.add_task(task)
            logger.info(f"Added web search task with ID: {task_id}")
            
            # Wait for the task to complete
            result = controller.wait_for_task(task_id)
            if "error" in result:
                logger.error(f"Task error: {result['error']}")
                return 1
            
            results = result.get("result", {}).get("results", [])
            for i, item in enumerate(results):
                print(f"{i+1}. {item.get('title', 'No title')}")
                print(f"   URL: {item.get('url', 'No URL')}")
                print(f"   {item.get('snippet', 'No snippet')}")
                print()
            
        else:
            parser.print_help()
            return 1
        
    finally:
        # Stop the controller
        controller.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())