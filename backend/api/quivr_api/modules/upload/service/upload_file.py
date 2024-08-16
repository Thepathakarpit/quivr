import mimetypes
from io import BufferedReader, FileIO
from uuid import UUID

from supabase.client import Client

from quivr_api.logger import get_logger
from quivr_api.models.settings import get_supabase_async_client, get_supabase_client
from quivr_api.modules.knowledge.service.knowledge_service import KnowledgeService

logger = get_logger(__name__)


async def check_file_exists(
    brain_id: str, file_identifier: str, knowledge_service: KnowledgeService
) -> bool:
    """
    brain_id : str
    file_identifier: str = computed file sha1
    Check if the file sha is already in storage;
    """
    supabase_client: Client = get_supabase_client()
    try:
        # Check if the file exists
        logger.info(f"Checking if file {file_identifier} exists.")
        # Get list of all knowledge
        # response = supabase_client.storage.from_("quivr").list(brain_id)
        response = await knowledge_service.get_all_knowledge(UUID(brain_id))

        # Check if the file_identifier is in the response
        file_exists = any(file.file_sha1 == file_identifier for file in response)
        logger.debug(f"File identifier: {file_identifier} exists: {file_exists}")
        if file_exists:
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"An error occurred while checking the file: {e}")
        return True


async def upload_file_storage(
    file: FileIO | BufferedReader | bytes,
    storage_path: str,
    upsert: bool = False,
):
    supabase_client = await get_supabase_async_client()
    mime_type, _ = mimetypes.guess_type(storage_path)
    logger.debug(
        f"Uploading file to {storage_path} using supabase. upsert={upsert}, mimetype={mime_type}"
    )

    if upsert:
        response = await supabase_client.storage.from_("quivr").update(
            storage_path,
            file,  # type: ignore
            file_options={
                "content-type": mime_type or "application/html",
                "upsert": "true",
                "cache-control": "3600",
            },
        )
        return response
    else:
        # check if file sha1 is already in storage
        try:
            response = await supabase_client.storage.from_("quivr").upload(
                storage_path,
                file,  # type: ignore
                file_options={
                    "content-type": mime_type or "application/html",
                    "upsert": "false",
                    "cache-control": "3600",
                },
            )
            return response
        except Exception as e:
            # FIXME: Supabase client to return the correct error
            if "The resource already exists" in str(e) and not upsert:
                raise FileExistsError(f"File {storage_path} already exists")
            raise e
