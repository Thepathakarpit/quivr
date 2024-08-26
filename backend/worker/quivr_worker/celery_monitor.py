import asyncio
import threading
from enum import Enum
from queue import Queue
from uuid import UUID

from attr import dataclass
from celery.result import AsyncResult
from quivr_api.celery_config import celery
from quivr_api.logger import get_logger
from quivr_api.modules.dependencies import async_engine
from quivr_api.modules.knowledge.repository.knowledges import KnowledgeRepository
from quivr_api.modules.knowledge.service.knowledge_service import KnowledgeService
from quivr_api.modules.notification.dto.inputs import NotificationUpdatableProperties
from quivr_api.modules.notification.entity.notification import NotificationsStatusEnum
from quivr_api.modules.notification.service.notification_service import (
    NotificationService,
)
from quivr_core.models import KnowledgeStatus
from sqlmodel.ext.asyncio.session import AsyncSession

logger = get_logger("notifier_service", "notifier_service.log")
notification_service = NotificationService()
queue = Queue()


class TaskStatus(str, Enum):
    FAILED = "task-failed"
    SUCCESS = "task-succeeded"


class TaskIdentifier(str, Enum):
    PROCESS_FILE_TASK = "process_file_task"
    PROCESS_CRAWL_TASK = "process_crawl_and_notify"


@dataclass
class TaskEvent:
    task_id: str
    brain_id: UUID
    task_name: TaskIdentifier
    notification_id: str
    knowledge_id: UUID
    status: TaskStatus


async def handler_loop():
    session = AsyncSession(async_engine, expire_on_commit=False, autoflush=False)
    knowledge_service = KnowledgeService(KnowledgeRepository(session))

    logger.info("Initialized knowledge_service. Listening to task event...")
    while True:
        event: TaskEvent = queue.get()
        if event.status == TaskStatus.FAILED:
            logger.error(
                f"task {event.task_id} process_file_task. Sending notifition {event.notification_id}"
            )
            notification_service.update_notification_by_id(
                event.notification_id,
                NotificationUpdatableProperties(
                    status=NotificationsStatusEnum.ERROR,
                    description=(
                        "An error occurred while processing the file"
                        if event.task_name == TaskIdentifier.PROCESS_FILE_TASK
                        else "An error occurred while processing the URL"
                    ),
                ),
            )
            logger.error(
                f"task {event.task_id} process_file_task  failed. Updating knowledge {event.knowledge_id} to Error"
            )
            if event.knowledge_id:
                await knowledge_service.update_status_knowledge(
                    event.knowledge_id, KnowledgeStatus.ERROR
                )
            logger.error(
                f"task {event.task_id} process_file_task . Updating knowledge {event.knowledge_id} status to Error"
            )

        if event.status == TaskStatus.SUCCESS:
            logger.info(
                f"task {event.task_id} process_file_task succeeded. Sending notification {event.notification_id}"
            )
            notification_service.update_notification_by_id(
                event.notification_id,
                NotificationUpdatableProperties(
                    status=NotificationsStatusEnum.SUCCESS,
                    description=(
                        "Your file has been properly uploaded!"
                        if event.task_name == TaskIdentifier.PROCESS_FILE_TASK
                        else "Your URL has been properly crawled!"
                    ),
                ),
            )
            if event.knowledge_id:
                await knowledge_service.update_status_knowledge(
                    knowledge_id=event.knowledge_id,
                    status=KnowledgeStatus.UPLOADED,
                    brain_id=event.brain_id,
                )
            logger.info(
                f"task {event.task_id} process_file_task failed. Updating knowledge {event.knowledge_id} to UPLOADED"
            )


def notifier(app):
    state = app.events.State()

    def handle_task_event(event):
        try:
            state.event(event)
            task = state.tasks.get(event["uuid"])
            task_result = AsyncResult(task.id, app=app)
            task_name, task_kwargs = task_result.name, task_result.kwargs

            if (
                task_name == "process_file_task"
                or task_name == "process_crawl_and_notify"
            ):
                logger.debug(f"Received Event : {task} - {task_name} {task_kwargs} ")
                notification_id = task_kwargs["notification_id"]
                knowledge_id = task_kwargs.get("knowledge_id", None)
                brain_id = task_kwargs.get("brain_id", None)
                event = TaskEvent(
                    task_id=task,
                    task_name=TaskIdentifier(task_name),
                    knowledge_id=knowledge_id,
                    brain_id=brain_id,
                    notification_id=notification_id,
                    status=TaskStatus(event["type"]),
                )
                queue.put(event)

        except Exception as e:
            logger.exception(f"handling event {event} raised exception: {e}")

    with app.connection() as connection:
        recv = app.events.Receiver(
            connection,
            handlers={
                "task-failed": handle_task_event,
                "task-succeeded": handle_task_event,
            },
        )
        recv.capture(limit=None, timeout=None, wakeup=True)


if __name__ == "__main__":
    logger.info("Started  quivr-notifier service...")

    def start_handler():
        asyncio.run(handler_loop())

    thread = threading.Thread(target=start_handler, daemon=True)
    thread.start()

    notifier(celery)
