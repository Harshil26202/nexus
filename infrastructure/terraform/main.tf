terraform {
  required_version = ">= 1.7.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.52"
    }
  }
  backend "azurerm" {
    resource_group_name  = "nexus-tfstate-rg"
    storage_account_name = "nexustfstate"
    container_name       = "tfstate"
    key                  = "nexus.terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault { purge_soft_delete_on_destroy = false }
  }
}

# ─── Resource Group ───────────────────────────────────────────────────────────
resource "azurerm_resource_group" "nexus" {
  name     = "nexus-${var.environment}-rg"
  location = var.location
  tags     = local.tags
}

# ─── Azure AI Foundry (OpenAI) ────────────────────────────────────────────────
resource "azurerm_cognitive_account" "openai" {
  name                  = "nexus-${var.environment}-oai"
  location              = var.openai_location
  resource_group_name   = azurerm_resource_group.nexus.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "nexus-${var.environment}-oai"
  tags                  = local.tags
}

resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-08-06"
  }
  scale { type = "GlobalStandard"; capacity = 100 }
}

resource "azurerm_cognitive_deployment" "gpt4o_mini" {
  name                 = "gpt-4o-mini"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini"
    version = "2024-07-18"
  }
  scale { type = "GlobalStandard"; capacity = 200 }
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                 = "text-embedding-3-large"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "text-embedding-3-large"
    version = "1"
  }
  scale { type = "Standard"; capacity = 120 }
}

# ─── Azure AI Search ──────────────────────────────────────────────────────────
resource "azurerm_search_service" "nexus" {
  name                = "nexus-${var.environment}-search"
  resource_group_name = azurerm_resource_group.nexus.name
  location            = azurerm_resource_group.nexus.location
  sku                 = "standard"
  replica_count       = var.environment == "production" ? 3 : 1
  partition_count     = var.environment == "production" ? 2 : 1
  tags                = local.tags
}

# ─── Azure Service Bus ────────────────────────────────────────────────────────
resource "azurerm_servicebus_namespace" "nexus" {
  name                = "nexus-${var.environment}-sb"
  location            = azurerm_resource_group.nexus.location
  resource_group_name = azurerm_resource_group.nexus.name
  sku                 = "Premium"
  capacity            = 1
  tags                = local.tags
}

resource "azurerm_servicebus_queue" "pipeline_events" {
  name         = "nexus-pipeline-events"
  namespace_id = azurerm_servicebus_namespace.nexus.id
  max_size_in_megabytes    = 5120
  default_message_ttl      = "P7D"
  lock_duration            = "PT5M"
  max_delivery_count       = 10
  dead_lettering_on_message_expiration = true
}

resource "azurerm_servicebus_queue" "agent_tasks" {
  name         = "nexus-agent-tasks"
  namespace_id = azurerm_servicebus_namespace.nexus.id
  max_size_in_megabytes = 5120
  default_message_ttl   = "P1D"
  max_delivery_count    = 5
}

resource "azurerm_servicebus_queue" "incident_events" {
  name         = "nexus-incident-events"
  namespace_id = azurerm_servicebus_namespace.nexus.id
  max_size_in_megabytes = 1024
  default_message_ttl   = "P30D"
}

# ─── Azure Cache for Redis ────────────────────────────────────────────────────
resource "azurerm_redis_cache" "nexus" {
  name                = "nexus-${var.environment}-redis"
  location            = azurerm_resource_group.nexus.location
  resource_group_name = azurerm_resource_group.nexus.name
  capacity            = var.environment == "production" ? 2 : 1
  family              = "C"
  sku_name            = var.environment == "production" ? "Standard" : "Basic"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"
  tags                = local.tags

  redis_configuration {
    maxmemory_policy = "allkeys-lru"
  }
}

# ─── Azure PostgreSQL Flexible Server ────────────────────────────────────────
resource "azurerm_postgresql_flexible_server" "nexus" {
  name                   = "nexus-${var.environment}-pg"
  resource_group_name    = azurerm_resource_group.nexus.name
  location               = azurerm_resource_group.nexus.location
  version                = "16"
  administrator_login    = var.db_admin_user
  administrator_password = var.db_admin_password
  storage_mb             = var.environment == "production" ? 131072 : 32768
  sku_name               = var.environment == "production" ? "GP_Standard_D4s_v3" : "B_Standard_B2ms"
  backup_retention_days  = var.environment == "production" ? 35 : 7
  geo_redundant_backup_enabled = var.environment == "production"
  tags                   = local.tags
}

resource "azurerm_postgresql_flexible_server_database" "nexus" {
  name      = "nexus"
  server_id = azurerm_postgresql_flexible_server.nexus.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# ─── Azure Kubernetes Service ─────────────────────────────────────────────────
resource "azurerm_kubernetes_cluster" "nexus" {
  name                = "nexus-${var.environment}-aks"
  location            = azurerm_resource_group.nexus.location
  resource_group_name = azurerm_resource_group.nexus.name
  dns_prefix          = "nexus-${var.environment}"
  kubernetes_version  = "1.30"

  default_node_pool {
    name                 = "system"
    node_count           = var.environment == "production" ? 3 : 1
    vm_size              = var.environment == "production" ? "Standard_D4s_v3" : "Standard_D2s_v3"
    os_disk_size_gb      = 128
    enable_auto_scaling  = var.environment == "production"
    min_count            = var.environment == "production" ? 3 : null
    max_count            = var.environment == "production" ? 10 : null
  }

  identity { type = "SystemAssigned" }

  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
  }

  monitor_metrics {}
  tags = local.tags
}

resource "azurerm_kubernetes_cluster_node_pool" "agents" {
  name                  = "agents"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.nexus.id
  vm_size               = "Standard_D4s_v3"
  node_count            = 2
  enable_auto_scaling   = true
  min_count             = 1
  max_count             = 20

  node_labels = { "nexus/role" = "agent-worker" }
  node_taints = ["nexus/agent=true:NoSchedule"]
}

# ─── Azure Container Registry ─────────────────────────────────────────────────
resource "azurerm_container_registry" "nexus" {
  name                = "nexus${var.environment}acr"
  resource_group_name = azurerm_resource_group.nexus.name
  location            = azurerm_resource_group.nexus.location
  sku                 = "Premium"
  admin_enabled       = false
  georeplications {
    location                = "westeurope"
    zone_redundancy_enabled = true
  }
  tags = local.tags
}

# ─── Azure Monitor + App Insights ────────────────────────────────────────────
resource "azurerm_log_analytics_workspace" "nexus" {
  name                = "nexus-${var.environment}-law"
  location            = azurerm_resource_group.nexus.location
  resource_group_name = azurerm_resource_group.nexus.name
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "production" ? 90 : 30
  tags                = local.tags
}

resource "azurerm_application_insights" "nexus" {
  name                = "nexus-${var.environment}-ai"
  location            = azurerm_resource_group.nexus.location
  resource_group_name = azurerm_resource_group.nexus.name
  workspace_id        = azurerm_log_analytics_workspace.nexus.id
  application_type    = "web"
  tags                = local.tags
}

# ─── Azure Key Vault ─────────────────────────────────────────────────────────
resource "azurerm_key_vault" "nexus" {
  name                        = "nexus-${var.environment}-kv"
  location                    = azurerm_resource_group.nexus.location
  resource_group_name         = azurerm_resource_group.nexus.name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "premium"
  soft_delete_retention_days  = 90
  purge_protection_enabled    = true
  enable_rbac_authorization   = true
  tags                        = local.tags
}

# ─── Azure Blob Storage ───────────────────────────────────────────────────────
resource "azurerm_storage_account" "nexus" {
  name                     = "nexus${var.environment}sa"
  resource_group_name      = azurerm_resource_group.nexus.name
  location                 = azurerm_resource_group.nexus.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "production" ? "GRS" : "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}

# ─── Azure Front Door ─────────────────────────────────────────────────────────
resource "azurerm_cdn_frontdoor_profile" "nexus" {
  count               = var.environment == "production" ? 1 : 0
  name                = "nexus-${var.environment}-afd"
  resource_group_name = azurerm_resource_group.nexus.name
  sku_name            = "Premium_AzureFrontDoor"
  tags                = local.tags
}

data "azurerm_client_config" "current" {}

locals {
  tags = {
    project     = "nexus"
    environment = var.environment
    managed_by  = "terraform"
  }
}
