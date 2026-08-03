{{- define "traceflow-ai.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "traceflow-ai.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "traceflow-ai.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "traceflow-ai.labels" -}}
app.kubernetes.io/name: {{ include "traceflow-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "traceflow-ai.serviceAccountName" -}}
{{- if .Values.serviceAccount.name -}}
{{- .Values.serviceAccount.name -}}
{{- else -}}
{{- include "traceflow-ai.fullname" . -}}
{{- end -}}
{{- end -}}

{{- define "traceflow-ai.secretName" -}}
{{- if .Values.anthropic.existingSecret -}}
{{- .Values.anthropic.existingSecret -}}
{{- else -}}
{{- printf "%s-anthropic" (include "traceflow-ai.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "traceflow-ai.outputClaimName" -}}
{{- if .Values.output.persistence.existingClaim -}}
{{- .Values.output.persistence.existingClaim -}}
{{- else -}}
{{- printf "%s-output" (include "traceflow-ai.fullname" .) -}}
{{- end -}}
{{- end -}}