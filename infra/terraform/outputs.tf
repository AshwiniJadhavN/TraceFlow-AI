output "traceflow_namespace" {
  value       = kubernetes_namespace_v1.traceflow.metadata[0].name
  description = "Namespace where TraceFlow AI was deployed."
}

output "traceflow_release" {
  value       = helm_release.traceflow_ai.name
  description = "Helm release name for the TraceFlow AI workload."
}

output "otlp_endpoint" {
  value       = local.otlp_endpoint
  description = "OTLP endpoint configured for the TraceFlow runtime."
}