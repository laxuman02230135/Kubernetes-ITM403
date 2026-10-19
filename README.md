# User management on Kubernetes

Student ID: 02230135. Namespace: `usermgmt-02230135`.

This assignment implements the platform, persistent PostgreSQL database, user management API, Ingress, and autoscaling manifests (milestones 1 to 5). Follow the Windows hostname setup below to access Ingress by name. The final report and demonstration are milestone 6.

## Platform

Follow [PLATFORM-SETUP.md](PLATFORM-SETUP.md) for the local tools, minikube startup workaround, metrics-server, Traefik, and VPA installation. Keep Docker Desktop running. All kubectl commands below explicitly target minikube.

## Create the database Secret

Create `k8s/01-db-secret.yaml` locally with the following structure. Replace the placeholder with a password for this lab. This file is excluded from Git. Do not commit the real password.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgres-secret
  namespace: usermgmt-02230135
type: Opaque
stringData:
  POSTGRES_DB: usermgmt
  POSTGRES_USER: usermgmt_admin
  POSTGRES_PASSWORD: "REPLACE_WITH_YOUR_OWN_PASSWORD"
```

Keep `POSTGRES_DB` consistent with `DB_NAME` in `04-api-configmap.yaml`. PostgreSQL's initial database credentials are created only when its data directory is empty; changing the Secret later does not change existing database passwords.

## Deploy from the project directory

In PowerShell:

```powershell
kubectl --context=minikube apply -f k8s/00-namespace.yaml
kubectl --context=minikube apply -f k8s/01-db-secret.yaml
kubectl --context=minikube apply -f k8s/02-postgres-service.yaml
kubectl --context=minikube apply -f k8s/03-postgres-statefulset.yaml
kubectl --context=minikube rollout status statefulset/postgres -n usermgmt-02230135 --timeout=300s
docker build -t usermgmt-api:1.0 ./app
$assignmentMinikube = "$env:LOCALAPPDATA/KubernetesAssignment/tools/minikube-1.38.1/out/minikube-windows-amd64.exe"
& $assignmentMinikube image load usermgmt-api:1.0
kubectl --context=minikube apply -f k8s/04-api-configmap.yaml
kubectl --context=minikube apply -f k8s/05-api-deployment.yaml
kubectl --context=minikube apply -f k8s/06-api-service.yaml
kubectl --context=minikube rollout status deployment/api -n usermgmt-02230135 --timeout=180s
```

Use a new versioned image tag for subsequent application changes and update both image references in the Deployment.

## Inspect and test

```powershell
kubectl --context=minikube get deploy,rs,pods,svc,pvc -n usermgmt-02230135
kubectl --context=minikube port-forward -n usermgmt-02230135 svc/api 8081:80
```

Keep port-forward running. Visit `http://localhost:8081/users` to view JSON in a browser. It initially returns an empty list because the persistence demonstration used a separate test table. Port 8081 is used here because another Docker project occupies 8080. For the assignment's example port, free port 8080, use `8080:80`, and run the test script with `-BaseUrl http://127.0.0.1:8080`.

In another PowerShell 7 terminal:

```powershell
./scripts/test-api.ps1
```

The script demonstrates all CRUD endpoints and error responses, removes only the users it created, and records output in `evidence/M3-api-tests.txt`.

To test that a simulated database outage affects readiness but not liveness:

```powershell
docker run --rm --mount "type=bind,source=$PWD/tests,target=/tests,readonly" usermgmt-api:1.0 python /tests/test_health.py
```

To repeat the database persistence demonstration (temporarily interrupts database access):

```powershell
./scripts/test-db-persistence.ps1
```

## Ingress: access by hostname (milestone 4)

Apply the route from a normal project terminal:

```powershell
kubectl --context=minikube apply -f k8s/07-api-ingress.yaml
```

Run the following in a separate terminal and keep it running:

```powershell
& "$env:LOCALAPPDATA/KubernetesAssignment/tools/minikube-1.38.1/out/minikube-windows-amd64.exe" tunnel --bind-address=127.0.0.1
```

Once per computer, open PowerShell **as Administrator** and run this script from the project folder:

```powershell
./scripts/set-local-hostname.ps1
```

It backs up the Windows hosts file and adds `127.0.0.1 usermgmt-02230135.local`, without changing unrelated entries. An existing conflicting address causes the script to stop for review.

Open `http://usermgmt-02230135.local/users` in your browser. No port 8081 is needed for this route. Verify from a normal project terminal:

```powershell
curl.exe --noproxy '*' http://usermgmt-02230135.local/users
./scripts/test-ingress.ps1
```

The script saves the Ingress description, hosts entry, successful request and wrong-host 404 to `evidence/M4-ingress-tests.txt`. Before the hosts entry is installed, `./scripts/test-ingress.ps1 -ResolveLocally` can verify routing using curl's temporary name mapping; this diagnostic mode does not prove Windows hostname setup is complete.

Request path: browser resolves the hostname to 127.0.0.1 → minikube tunnel → Traefik controller matches the Ingress host and path → api Service backend → ready API Pod → PostgreSQL. The Ingress is the routing configuration; Traefik handles the traffic. A different Host header has no matching rule and receives Traefik's 404 response. A default browser page at `/` also returns 404 because our API routes are `/users`, `/healthz`, and `/ready`.

The Windows Docker-driver tunnel approach is documented in [minikube's access guide](https://minikube.sigs.k8s.io/docs/handbook/accessing/). Keep Docker Desktop, minikube, and the tunnel running for browser access. The separate API port-forward on 8081 is only needed for the earlier direct-access demonstration.

## Autoscaling (milestone 5)

With the API running and hostname access working:

```powershell
kubectl --context=minikube top pods -n usermgmt-02230135
kubectl --context=minikube apply -f k8s/08-api-hpa.yaml -f k8s/09-postgres-vpa.yaml
kubectl --context=minikube get hpa,vpa -n usermgmt-02230135
```

`08-api-hpa.yaml` creates an autoscaling/v2 HPA for Deployment `api`: minimum 2 replicas, maximum 6, and average CPU utilisation target 50%. Each API container requests 100m CPU, so 50% corresponds to approximately 50m usage per Pod, averaged across the eligible API Pods. This percentage is relative to the request, not the CPU limit or the entire computer.

`09-postgres-vpa.yaml` targets StatefulSet `postgres` with updateMode `Off`. It collects CPU and memory recommendations (lower bound, target and upper bound) without applying them or restarting the database. A short lab observation is evidence that recommendations work, not enough history for production sizing.

Run the load test from the Windows host using Python 3 (already installed on this computer; no additional packages required):

```powershell
python scripts/test-autoscaling.py
```

The script sends only GET requests to `http://usermgmt-02230135.local/users` with 10 concurrent clients for 180 seconds, then observes for 420 seconds without load. Keep the minikube tunnel running. It records HPA CPU and replica counts every 30 seconds into a new timestamped `evidence/M5-*` directory. `timeline.csv` is the report table; `observations.jsonl` contains raw Kubernetes snapshots; `summary.json` records response counts and pass/fail; the other files capture HPA events, VPA recommendations and final metrics. The first HPA sample can have missing CPU metrics while the controller starts collecting data. Pass/fail also checks HTTP errors and new container restarts. Use `--concurrency 50` to repeat the heavier stress test, which may overload this small database.

In another terminal, observe the same test live:

```powershell
kubectl --context=minikube get hpa -n usermgmt-02230135 -w
```

Press Ctrl+C to stop that display; it does not stop the autoscaler. The HPA has a 300-second scale-down stabilisation window, so replicas intentionally remain elevated for several minutes after traffic stops. Do not manually scale or reapply the API Deployment during observation: its `replicas: 2` value could interrupt the HPA's experiment.

This cluster's metrics-server samples every 60 seconds (`--metric-resolution=60s`). The recorder's 30-second samples can therefore repeat the same CPU percentage. A delayed CPU measurement can even trigger one last scale-up shortly after the load ends; use the recorded timestamps when explaining this.

To export a completed run as a report figure, use `python scripts/plot-autoscaling.py evidence/M5-<timestamp>`, replacing the directory with your actual run. This optional plotting step requires matplotlib, which is installed on this computer. The load test itself uses only the Python standard library.

Why separate HPA and VPA? HPA changes the **number of API Pods** using CPU usage divided by CPU requests. An active VPA changing those same requests would change the percentage the HPA uses, potentially making the two controllers react to each other. This design assigns HPA to the API and recommendation-only VPA to PostgreSQL. PostgreSQL remains one Pod with stable storage.

Reference: [Kubernetes HPA behaviour](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/) and [VPA update modes](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/api.md).

Verified on 9 October 2026: [the ten-client run](evidence/M5-20261009T174018Z/summary.json) completed 6,002 successful requests with no errors or new restarts and showed 2 → 5 → 6 → 3 → 2 API Pods. See its [chart](evidence/M5-20261009T174018Z/autoscaling.png), [timeline](evidence/M5-20261009T174018Z/timeline.csv), and [troubleshooting notes](evidence/M5-troubleshooting.md). The earlier 50-client run is retained separately because it exposed overload errors.

## Report and demonstration (milestone 6)

The report review copy is [output/pdf/Kubernetes_UserMgmt_Report_02230135.pdf](output/pdf/Kubernetes_UserMgmt_Report_02230135.pdf): eight main pages and ten manifest appendix pages. [DEMO-GUIDE.md](DEMO-GUIDE.md) provides a ten-minute sequence, exact commands, likely questions and an actual-screenshot checklist. The report includes recorded command excerpts, not fabricated terminal screenshots. Actual screenshot collection, a fresh-cluster rehearsal and a published Git URL remain submission tasks.

The report can be regenerated with `python scripts/build-report.py` in an environment with ReportLab and pypdf installed. It reads only non-secret manifests and generates a placeholder Secret template. These documentation dependencies are not required by the deployed API.

## How the API works

- `app/app.py`: Flask routes, input validation, status codes, and SQL operations.
- `app/db.py`: reads configuration and credentials from environment variables.
- `app/init_db.py`: creates the users table in an init container; a transaction lock serialises simultaneous schema creation.
- `app/Dockerfile`: packages Python and dependencies and runs Gunicorn as a non-root user on port 8000.
- `04-api-configmap.yaml`: non-secret database host, port, and name.
- `05-api-deployment.yaml`: two API replicas, init containers, Secret references, resource requests and limits, and health probes.
- `06-api-service.yaml`: exposes ready API Pods internally on port 80, forwarding to their port 8000.

`GET /healthz` reports process liveness without contacting PostgreSQL. `GET /ready` performs a database query and returns 503 when it cannot connect. CPU requests of 100m per API container provide the denominator for the later HPA target.

POST and PUT require a JSON object containing both `name` and `email`. Emails are normalised to lowercase, with uniqueness enforced in PostgreSQL. Parameterised SQL keeps user values separate from SQL syntax. All API replicas share the same database.

This is a local assignment API with no authentication or graphical frontend. Do not expose it as a public user-management system.
