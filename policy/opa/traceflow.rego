package traceflow

deny[msg] {
  input.kind == "Job"
  not input.spec.template.spec.securityContext.runAsNonRoot
  msg := "Job pod spec must set runAsNonRoot=true"
}

deny[msg] {
  input.kind == "CronJob"
  not input.spec.jobTemplate.spec.template.spec.securityContext.runAsNonRoot
  msg := "CronJob pod spec must set runAsNonRoot=true"
}

deny[msg] {
  input.kind == "Job"
  some i
  endswith(input.spec.template.spec.containers[i].image, ":latest")
  msg := "Job containers must not use latest tags"
}

deny[msg] {
  input.kind == "CronJob"
  some i
  endswith(input.spec.jobTemplate.spec.template.spec.containers[i].image, ":latest")
  msg := "CronJob containers must not use latest tags"
}

deny[msg] {
  input.kind == "Job"
  not job_has_secret_env
  msg := "Job must source ANTHROPIC_API_KEY from a Secret"
}

deny[msg] {
  input.kind == "CronJob"
  not cronjob_has_secret_env
  msg := "CronJob must source ANTHROPIC_API_KEY from a Secret"
}

job_has_secret_env {
  some i
  some j
  env := input.spec.template.spec.containers[i].env[j]
  env.name == "ANTHROPIC_API_KEY"
  env.valueFrom.secretKeyRef.name != ""
  env.valueFrom.secretKeyRef.key == "ANTHROPIC_API_KEY"
}

cronjob_has_secret_env {
  some i
  some j
  env := input.spec.jobTemplate.spec.template.spec.containers[i].env[j]
  env.name == "ANTHROPIC_API_KEY"
  env.valueFrom.secretKeyRef.name != ""
  env.valueFrom.secretKeyRef.key == "ANTHROPIC_API_KEY"
}