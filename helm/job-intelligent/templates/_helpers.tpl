{{/* Common labels on every object (selectors stay on the short "app" label). */}}
{{- define "ji.labels" -}}
app.kubernetes.io/part-of: job-intelligent
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{- define "ji.secretName" -}}
{{- default "app-secrets" .Values.existingSecret -}}
{{- end }}

{{/* Restart pods when config or secrets change. */}}
{{- define "ji.checksums" -}}
checksum/config: {{ include (print $.Template.BasePath "/config.yaml") . | sha256sum }}
checksum/secret: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
{{- end }}

{{/* Environment shared by every Airflow container (init Job, webserver, scheduler). */}}
{{- define "ji.airflowEnv" -}}
envFrom:
  - configMapRef: { name: app-config }
  - configMapRef: { name: airflow-config }
  - secretRef:    { name: {{ include "ji.secretName" . }} }
env:
  - name: AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
    value: postgresql+psycopg2://$(DB_USER):$(DB_PASS)@$(DB_HOST):$(DB_PORT)/$(DB_NAME)
  - name: AIRFLOW__CORE__FERNET_KEY
    value: $(FERNET_KEY)
  - name: AIRFLOW__WEBSERVER__SECRET_KEY
    value: $(SECRET_KEY)
  - name: SELENIUM_URL
    value: http://selenium:4444/wd/hub
{{- end }}

{{- define "ji.waitForMigrations" -}}
- name: wait-for-migrations   # blocks until the airflow-init hook has migrated the DB
  image: {{ .Values.images.airflow }}
  imagePullPolicy: {{ .Values.imagePullPolicy }}
  args: ["db", "check-migrations", "--migration-wait-timeout", "600"]
  {{- include "ji.airflowEnv" . | nindent 2 }}
{{- end }}
