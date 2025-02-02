variable "deepseek_api_key" {
  description = "API key for Deepseek"
  type        = string
}

variable "groq_api_key" {
  description = "API key for Groq"
  type        = string
}

variable "perplexity_api_key" {
  description = "API key for Perplexity"
  type        = string
}

variable "gumtree_iap_token" {
  description = "IAP token for Gumtree"
  type        = string
}

variable "deepseek_backend_port" {
  description = "Port for the backend service"
  type        = number
  default     = 8083
}

variable "deepseek_frontend_port" {
  description = "Port for the frontend service"
  type        = number
  default     = 8082
}

variable "network_name" {
  description = "Name of the Docker network"
  type        = string
  default     = "deepseek-network"
} 