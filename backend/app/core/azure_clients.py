"""Singleton Azure SDK client factory."""
from functools import lru_cache

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents.aio import SearchClient
from azure.servicebus.aio import ServiceBusClient
from azure.storage.blob.aio import BlobServiceClient
from openai import AsyncAzureOpenAI, AsyncOpenAI

from app.core.config import settings


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    """Return Azure OpenAI client when credentials are present, otherwise standard OpenAI."""
    if settings.use_azure_openai:
        return AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


@lru_cache
def get_search_client(index: str) -> SearchClient:
    return SearchClient(
        endpoint=settings.AZURE_AI_SEARCH_ENDPOINT,
        index_name=index,
        credential=DefaultAzureCredential() if settings.is_production else AzureKeyCredential(
            settings.AZURE_AI_SEARCH_KEY
        ),
    )


@lru_cache
def get_service_bus_client() -> ServiceBusClient:
    return ServiceBusClient.from_connection_string(
        settings.AZURE_SERVICE_BUS_CONNECTION_STRING,
        logging_enable=not settings.is_production,
    )


@lru_cache
def get_blob_client() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(
        settings.AZURE_STORAGE_CONNECTION_STRING
    )
