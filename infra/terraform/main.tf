resource "kubernetes_namespace_v1" "traceflow" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/name" = "traceflow-ai"
      "app.kubernetes.io/part-of" = "traceflow-ai"
    }
  }
}

locals {
  collector_endpoint = "http://otel-collector.${var.observability_namespace}.svc.cluster.local:4318/v1/traces"
  otlp_endpoint      = var.enable_otel_collector ? local.collector_endpoint : var.otlp_endpoint
}

resource "helm_release" "otel_collector" {
  count            = var.enable_otel_collector ? 1 : 0
  name             = "otel-collector"
  namespace        = var.observability_namespace
  create_namespace = true
  repository       = "https://open-telemetry.github.io/opentelemetry-helm-charts"
  chart            = "opentelemetry-collector"
  version          = "0.111.1"

  values = [
    yamlencode({
      fullnameOverride = "otel-collector"
      mode = "deployment"
      config = {
        receivers = {
          otlp = {
            protocols = {
              http = {}
            }
          }
        }
        exporters = {
          debug = {}
        }
        service = {
          pipelines = {
            traces = {
              receivers = ["otlp"]
              exporters = ["debug"]
            }
          }
        }
      }
    })
  ]
}

resource "helm_release" "traceflow_ai" {
  name      = "traceflow-ai"
  namespace = kubernetes_namespace_v1.traceflow.metadata[0].name
  chart     = "${path.module}/../../charts/traceflow-ai"

  depends_on = [kubernetes_namespace_v1.traceflow]

  values = [
    yamlencode({
      image = {
        repository = var.image_repository
        tag        = var.image_tag
      }
      anthropic = {
        apiKey = var.anthropic_api_key
      }
      workload = {
        command      = var.workload_command
        requirement  = var.requirement
        systemContext = var.system_context
        environment  = "production"
        otlpEndpoint = local.otlp_endpoint
      }
      job = {
        enabled = var.job_enabled
      }
      cronjob = {
        enabled  = var.cronjob_enabled
        schedule = var.cron_schedule
      }
    })
  ]
}