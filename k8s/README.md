# Déploiement Kubernetes — Job Intelligent

Conteneurisation et déploiement de l'application sur un cluster local **Minikube**.

## Architecture

```
 Navigateur ──► NodePort 30080 ──► Service frontend ──► 2 pods nginx (React)
                                                          │  /api/*  (proxy)
                                                          ▼
                                     Service api (ClusterIP) ──► 2 pods FastAPI
                                                          │
                                                          ▼
                              Service postgres (headless) ──► StatefulSet postgres-0
                                                          ▲       └─ PVC 1Gi (données)
                                                          │ bronze → silver → gold
 Navigateur ──► NodePort 30081 ──► airflow-webserver      │
                                   airflow-scheduler ─────┘  (DAG daily_job_scraping, 12:00 UTC)
                                        │  ├─ API France Travail (Internet)
                                        │  └─ Service selenium:4444 ──► Chrome (LinkedIn)
                                   Job airflow-init (db migrate + compte admin, une seule fois)
```

| Fichier | Contenu |
|---|---|
| `k8s/namespace.yaml` | Namespace `job-intelligent` |
| `k8s/configmap.yaml` | Configuration non sensible (hôte DB, nom DB, CORS…) |
| `k8s/secrets.env` (non versionné) | `DB_PASS`, `JWT_SECRET`, clés Airflow, identifiants France Travail → Secret `app-secrets` |
| `k8s/airflow.yaml` | ConfigMap Airflow, Job `airflow-init`, Deployments webserver + scheduler, Service NodePort 30081 |
| `k8s/selenium.yaml` | Chrome headless (Selenium Grid) pour le scraper LinkedIn + Service |
| `k8s/postgres.yaml` | StatefulSet + volume persistant + Service headless |
| `k8s/api.yaml` | Deployment FastAPI (2 réplicas) + Service ClusterIP |
| `k8s/frontend.yaml` | Deployment nginx (2 réplicas) + Service NodePort |
| `kustomization.yaml` | Assemble le tout, génère la ConfigMap `postgres-init` depuis `sql/init.sql` |

## Sondes de santé

| Composant | startupProbe | livenessProbe | readinessProbe |
|---|---|---|---|
| postgres | `pg_isready` (2 min max, 1er démarrage) | `pg_isready` | `pg_isready` |
| api | `GET /live` | `GET /live` (processus seulement) | `GET /health` (teste la DB) |
| frontend | — | `GET /healthz` | `GET /healthz` |
| airflow-webserver | `GET /health` (5 min max) | `GET /health` | `GET /health` |
| airflow-scheduler | `GET :8974/health` | `GET :8974/health` | — |
| selenium | `GET /status` | `GET /status` | `GET /status` |

Les pods Airflow ont un *initContainer* `airflow db check-migrations` : ils attendent que
le Job `airflow-init` ait migré la base avant de démarrer.

Choix important : la **liveness** de l'API n'interroge pas la base. Si Postgres tombe,
les pods API deviennent *NotReady* (retirés du Service) au lieu d'être redémarrés
en boucle, ce qui n'aurait rien réparé.

## Prérequis (Windows)

Dans un PowerShell **administrateur** :

```powershell
choco install -y docker-desktop minikube kubernetes-cli kubernetes-helm
```

Redémarrer, lancer Docker Desktop (backend WSL2), puis vérifier :

```powershell
docker version; minikube version; kubectl version --client; helm version
```

## Déploiement

Deux méthodes équivalentes. **Le cluster actuel est géré par Helm** : ne pas mélanger
les deux sur le même namespace (Helm et `kubectl apply -k` se disputeraient les ressources).

### Avec Helm (méthode actuelle)

```powershell
.\scripts\deploy-helm.ps1          # install / upgrade (ajouter -Build pour reconstruire les images)
helm -n job-intelligent list       # release, révision, statut
helm -n job-intelligent history job-intelligent
helm -n job-intelligent rollback job-intelligent <REVISION>
```

Chart : `helm/job-intelligent/`

| Fichier | Contenu |
|---|---|
| `Chart.yaml` | Nom et version du chart |
| `values.yaml` | Tout ce qui est paramétrable : images, réplicas, ressources, NodePorts, activation d'Airflow/Selenium |
| `templates/_helpers.tpl` | Labels communs, bloc d'environnement Airflow partagé, checksums |
| `templates/*.yaml` | Mêmes objets que `k8s/` (mêmes noms et sélecteurs) |
| `files/init.sql` | Copie de `sql/init.sql` (Helm ne lit pas hors du chart ; `deploy-helm.ps1` la resynchronise) |

Apports par rapport aux manifestes bruts :
- **Paramétrage** : `helm upgrade ... --set api.replicas=3` ou `--set airflow.enabled=false`.
- **Secrets hors du chart** : `deploy-helm.ps1` lit `k8s/secrets.env` et les passe dans un
  fichier temporaire supprimé aussitôt ; le chart refuse de s'installer s'il en manque un.
- **Redémarrage automatique** des pods quand la configuration ou un secret change
  (annotations `checksum/config` et `checksum/secret`).
- **`airflow-init` devient un hook Helm** (`post-install,post-upgrade`), rejoué à chaque upgrade.
- **Historique et rollback** des déploiements.

La première exécution de `deploy-helm.ps1` a **adopté** les ressources créées par
`kubectl apply -k` (labels/annotations Helm) : rien n'a été supprimé, le volume Postgres
et ses données ont été conservés.

### Avec kustomize (manifestes bruts)

```powershell
.\scripts\deploy.ps1
minikube service frontend -n job-intelligent   # ouvre l'application
```

Le script démarre Minikube, génère `k8s/secrets.env` avec des valeurs aléatoires,
construit les images directement dans Minikube (`minikube image build`, pas de
registre nécessaire), applique `kubectl apply -k .` et attend que tout soit prêt.

Commandes utiles :

```powershell
kubectl -n job-intelligent get all,pvc
kubectl -n job-intelligent logs -l app=api -f
kubectl -n job-intelligent port-forward svc/api 8000:8000   # Swagger : http://localhost:8000/docs
kubectl delete -k .                                         # tout supprimer (PVC compris)
```

## Preuve de redémarrage

```powershell
.\scripts\prove-restart.ps1     # sortie enregistrée dans restart-proof.log
```

1. **Crash du conteneur API** : le processus uvicorn est arrêté → le kubelet relance le
   conteneur, `RESTARTS` passe de 0 à 1.
2. **Suppression d'un pod API** : le Deployment recrée immédiatement un pod pour revenir à 2/2.
3. **Suppression du pod Postgres** : le StatefulSet recrée `postgres-0` et une ligne
   écrite avant la suppression est relue après → les données survivent grâce au PVC
   (le nombre d'offres dans `gold_jobs` est identique avant et après).
4. **Suppression du pod scheduler Airflow** : le Deployment le recrée et le DAG
   `daily_job_scraping` est de nouveau chargé et actif.

Pendant que Postgres redémarre, les pods API passent *NotReady* (readiness 500) sans
être redémarrés : c'est l'effet voulu de la séparation `/live` / `/health`.

## Airflow

```powershell
minikube service airflow-webserver -n job-intelligent   # login : admin / AIRFLOW_ADMIN_PASSWORD de k8s/secrets.env
kubectl -n job-intelligent exec deploy/airflow-scheduler -- airflow dags trigger daily_job_scraping   # lancer sans attendre 12:00
kubectl -n job-intelligent port-forward svc/selenium 7900:7900   # voir Chrome : http://localhost:7900 (mot de passe "secret")
```

Différences avec docker-compose :
- `dags/` et `scrapers/` sont **copiés dans l'image** Airflow (pas de montage de dossiers
  en Kubernetes) : après une modification du code, relancer `.\scripts\deploy.ps1`.
- Le service `airflow-init` devient un **Job** Kubernetes (tâche exécutée une fois).
- `shm_size: 2gb` de Selenium devient un volume `emptyDir` en mémoire monté sur `/dev/shm`.

## Limites connues

- Les fichiers d'échange du DAG (`/tmp/*.json`) et les logs Airflow vivent dans le pod
  scheduler : ils sont perdus si ce pod redémarre (les données en base, elles, restent).
- Ressources : Minikube reçoit 4 CPU / 7 Go (limite Docker fixée par `.wslconfig`).
  Le scraping LinkedIn (4 Chrome en parallèle) est la partie la plus gourmande.
