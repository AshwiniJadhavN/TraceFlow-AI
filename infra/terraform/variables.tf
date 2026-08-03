variable "namespace" {
  type        = string
  description = "Namespace for the TraceFlow AI workload."
  default     = "traceflow-ai"
}

variable "observability_namespace" {
  type        = string
  description = "Namespace for the OpenTelemetry Collector."
  default     = "observability"
}

variable "image_repository" {
  type        = string
  description = "Container repository for TraceFlow AI."
}

variable "image_tag" {
  type        = string
  description = "Container tag for TraceFlow AI."
  default     = "v1.0.0"
}

variable "anthropic_api_key" {
  type        = string
  description = "Anthropic API key injected into the runtime secret."
  sensitive   = true
}

variable "requirement" {
  type        = string
  description = "Requirement payload that the Job or CronJob will analyze."
}

variable "system_context" {
  type        = string
  description = "Optional system context for system-analyze mode."
  default     = ""
}

variable "workload_command" {
  type        = string
  description = "Either analyze or system-analyze."
  default     = "analyze"
}

variable "job_enabled" {
  type        = bool
  description = "Whether to create the one-shot Job."
  default     = true
}

variable "cronjob_enabled" {
  type        = bool
  description = "Whether to create the scheduled CronJob."
  default     = false
}

variable "cron_schedule" {
  type        = string
  description = "Cron schedule when the scheduled workload is enabled."
  default     = "0 4 * * *"
}

variable "enable_otel_collector" {
  type        = bool
  description = "Whether to install an OpenTelemetry Collector via Helm."
  default     = true
}

variable "otlp_endpoint" {
  type        = string
  description = "Explicit OTLP HTTP endpoint. Ignored when the collector is installed by Terraform."
  default     = ""
}