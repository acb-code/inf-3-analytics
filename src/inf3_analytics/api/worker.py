"""Background worker for processing pipeline tasks from the queue.

Run with: uv run inf3-worker
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from inf3_analytics.api.config import get_settings
from inf3_analytics.api.models import PipelineStep, TriggerPipelineRequest
from inf3_analytics.api.pipeline_executor import execute_pipeline, execute_single_step
from inf3_analytics.api.queue import TaskQueue
from inf3_analytics.api.registry import RunRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class Worker:
    """Pipeline task worker with graceful shutdown support."""

    def __init__(
        self,
        queue: TaskQueue,
        registry: RunRegistry,
        poll_interval: float = 1.0,
    ) -> None:
        """Initialize the worker.

        Args:
            queue: Task queue to process
            registry: Run registry for status updates
            poll_interval: Seconds between queue checks when idle
        """
        self._queue = queue
        self._registry = registry
        self._poll_interval = poll_interval
        self._running = False
        self._current_task_id: str | None = None

    def _handle_signal(self, signum: int, _frame: object) -> None:
        """Handle shutdown signals gracefully."""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received {sig_name}, shutting down gracefully...")
        self._running = False

    def run(self) -> None:
        """Main worker loop."""
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        self._running = True
        logger.info("Worker started, waiting for tasks...")

        # Recover any stale tasks on startup
        recovered = self._queue.recover_stale()
        if recovered > 0:
            logger.warning(f"Recovered {recovered} stale task(s) from previous worker crash")

        while self._running:
            task = self._queue.claim_next()

            if task is None:
                # No tasks, wait before checking again
                time.sleep(self._poll_interval)
                continue

            self._current_task_id = task.task_id
            logger.info(f"Processing task {task.task_id} for run {task.run_id}")

            try:
                # Build request object
                request = TriggerPipelineRequest(**task.request)

                if task.step is not None:
                    # Execute single step
                    step = PipelineStep(task.step)
                    success, message = execute_single_step(
                        registry=self._registry,
                        run_id=task.run_id,
                        video_path=task.video_path,
                        run_root=task.run_root,
                        video_basename=task.video_basename,
                        step=step,
                        request=request,
                    )
                    if success:
                        self._queue.complete(task.task_id)
                        logger.info(f"Task {task.task_id} completed successfully")
                    else:
                        self._queue.fail(task.task_id, message)
                        logger.error(f"Task {task.task_id} failed: {message[:200]}")
                else:
                    # Execute full pipeline
                    execute_pipeline(
                        registry=self._registry,
                        run_id=task.run_id,
                        video_path=task.video_path,
                        run_root=task.run_root,
                        video_basename=task.video_basename,
                        request=request,
                    )

                    # Check final status
                    run = self._registry.get_run(task.run_id)
                    if run and run.status.value == "completed":
                        self._queue.complete(task.task_id)
                        logger.info(f"Task {task.task_id} completed successfully")
                    else:
                        error_msg = "Pipeline failed"
                        steps = self._registry.get_pipeline_steps(task.run_id)
                        for step_info in steps:
                            if step_info.error_message:
                                error_msg = step_info.error_message
                                break
                        self._queue.fail(task.task_id, error_msg)
                        logger.error(f"Task {task.task_id} failed: {error_msg[:200]}")

            except Exception as e:
                error_msg = str(e)
                self._queue.fail(task.task_id, error_msg)
                logger.exception(f"Task {task.task_id} failed with exception: {error_msg}")

            finally:
                self._current_task_id = None

        logger.info("Worker stopped")


def main() -> int:
    """Main entry point for the worker CLI."""
    parser = argparse.ArgumentParser(
        prog="inf3-worker",
        description="Background worker for processing pipeline tasks",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Seconds between queue checks when idle (default: 1.0)",
    )
    parser.add_argument(
        "--queue-dir",
        type=Path,
        default=None,
        help="Queue directory (default: .inf3-analytics/queue)",
    )
    args = parser.parse_args()

    # Get settings
    settings = get_settings()

    # Initialize queue and registry
    queue = TaskQueue(base_dir=args.queue_dir)
    registry = RunRegistry(settings.inf3_registry_path)

    # Create and run worker
    worker = Worker(
        queue=queue,
        registry=registry,
        poll_interval=args.poll_interval,
    )

    try:
        worker.run()
        return 0
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
        return 0
    except Exception as e:
        logger.exception(f"Worker failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
