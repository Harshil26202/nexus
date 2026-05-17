output "resource_group_name" {
  description = "Name of the Azure resource group"
  value       = azurerm_resource_group.nexus.name
}

output "aks_cluster_name" {
  description = "Name of the AKS cluster"
  value       = azurerm_kubernetes_cluster.nexus.name
}

output "aks_kubeconfig" {
  description = "Kubeconfig for AKS cluster"
  value       = azurerm_kubernetes_cluster.nexus.kube_config_raw
  sensitive   = true
}

output "acr_login_server" {
  description = "Azure Container Registry login server URL"
  value       = azurerm_container_registry.nexus.login_server
}

output "openai_endpoint" {
  description = "Azure OpenAI endpoint URL"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "openai_api_key" {
  description = "Azure OpenAI primary API key"
  value       = azurerm_cognitive_account.openai.primary_access_key
  sensitive   = true
}

output "search_endpoint" {
  description = "Azure AI Search endpoint"
  value       = "https://${azurerm_search_service.nexus.name}.search.windows.net"
}

output "search_primary_key" {
  description = "Azure AI Search admin key"
  value       = azurerm_search_service.nexus.primary_key
  sensitive   = true
}

output "service_bus_connection_string" {
  description = "Azure Service Bus primary connection string"
  value       = azurerm_servicebus_namespace.nexus.default_primary_connection_string
  sensitive   = true
}

output "redis_hostname" {
  description = "Azure Redis Cache hostname"
  value       = azurerm_redis_cache.nexus.hostname
}

output "redis_primary_key" {
  description = "Azure Redis Cache primary key"
  value       = azurerm_redis_cache.nexus.primary_access_key
  sensitive   = true
}

output "postgres_fqdn" {
  description = "Azure PostgreSQL Flexible Server FQDN"
  value       = azurerm_postgresql_flexible_server.nexus.fqdn
}

output "appinsights_connection_string" {
  description = "Azure Application Insights connection string"
  value       = azurerm_application_insights.nexus.connection_string
  sensitive   = true
}

output "key_vault_uri" {
  description = "Azure Key Vault URI"
  value       = azurerm_key_vault.nexus.vault_uri
}

output "storage_account_name" {
  description = "Azure Storage Account name"
  value       = azurerm_storage_account.nexus.name
}
