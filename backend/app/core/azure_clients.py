"""Singleton Azure SDK client factory."""
from functools import lru_cache

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.search.documents.aio import SearchClient
from azure.servicebus.aio import ServiceBusClient
from azure.storage.blob.aio import BlobServiceClient
from openai import AsyncAzureOpenAI

from app.core.config import settings


@lru_cache
def get_openai_client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )


@lru_cache
def get_search_client(index: str) -> SearchClient:
    return SearchClient(
        endpoint=settings.AZURE_AI_SEARCH_ENDPOINT,
        index_name=index,
        credential=DefaultAzureCredential() if settings.is_production
        else __import__("azure.core.credentials", fromlist=["AzureKeyCredential"]).AzureKeyCredential(
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
