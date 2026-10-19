"""Build the assignment report from verified evidence and safe manifest sources."""
from pathlib import Path
import json
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Preformatted, Image
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'output/pdf'
OUT.mkdir(parents=True, exist_ok=True)
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Body', fontName='Helvetica', fontSize=10, leading=14, spaceAfter=8, textColor=colors.HexColor('#253348')))
styles.add(ParagraphStyle(name='SmallNote', parent=styles['Body'], fontSize=8, leading=11, textColor=colors.HexColor('#526078')))
styles.add(ParagraphStyle(name='CodeSmall', fontName='Courier', fontSize=7.5, leading=9.2, spaceAfter=8))
styles['Heading1'].textColor = colors.HexColor('#133f72')
styles['Heading1'].fontSize = 20
styles['Heading1'].leading = 24
styles['Heading2'].textColor = colors.HexColor('#133f72')
story = []

def p(text, style='Body'):
    story.append(Paragraph(text, styles[style]))

def heading(text):
    p(text, 'Heading2')

def page(title):
    if story:
        story.append(PageBreak())
    p(title, 'Heading1')
    story.append(Spacer(1, 7))

def code(text):
    story.append(Preformatted(text.strip(), styles['CodeSmall']))

def table(headers, rows, widths):
    data = [[Paragraph(escape(str(v)), styles['SmallNote']) for v in row] for row in [headers] + rows]
    result = Table(data, colWidths=widths, hAlign='LEFT', repeatRows=1)
    result.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e5eef9')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor('#8baaca')),
        ('LINEBELOW', (0,1), (-1,-1), .3, colors.HexColor('#dce3eb')),
        ('LEFTPADDING', (0,0), (-1,-1), 7), ('RIGHTPADDING', (0,0), (-1,-1), 7),
        ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.extend([result, Spacer(1, 10)])

def architecture():
    d = Drawing(490, 326)
    def box(x, y, w, h, lines, color='#edf4fc'):
        d.add(Rect(x, y, w, h, rx=6, ry=6, fillColor=colors.HexColor(color), strokeColor=colors.HexColor('#8baaca')))
        for i, line in enumerate(lines):
            d.add(String(x+w/2, y+h/2+(len(lines)-1)*6-i*12, line, textAnchor='middle', fontName='Helvetica', fontSize=9, fillColor=colors.HexColor('#173552')))
    def arrow(x1,y1,x2,y2, dashed=False):
        d.add(Line(x1,y1,x2,y2, strokeColor=colors.HexColor('#3e668d'), strokeWidth=1.2, strokeDashArray=[3,3] if dashed else None))
        if y1 == y2:
            s = 1 if x2>x1 else -1
            pts=[x2,y2,x2-5*s,y2+3,x2-5*s,y2-3]
        else:
            s = 1 if y2>y1 else -1
            pts=[x2,y2,x2-3,y2-5*s,x2+3,y2-5*s]
        d.add(Polygon(pts, fillColor=colors.HexColor('#3e668d'), strokeColor=None))
    box(5,279,155,38,['Browser / PowerShell','usermgmt-02230135.local'])
    box(195,279,165,38,['Windows hosts: 127.0.0.1','minikube tunnel'])
    arrow(160,298,195,298)
    d.add(Rect(5,3,480,255, fillColor=None, strokeColor=colors.HexColor('#afbdcf'), strokeDashArray=[4,3]))
    d.add(String(15,244,'minikube on Docker Desktop',fontSize=8,fontName='Helvetica'))
    d.add(String(15,232,'Application namespace: usermgmt-02230135',fontSize=8,fontName='Helvetica'))
    box(195,188,165,39,['Traefik controller','Ingress: host + / prefix'])
    arrow(277,279,277,227)
    box(195,127,165,39,['api Service :80','API Deployment: 2-6 Pods :8000'])
    arrow(277,188,277,166)
    box(195,66,165,39,['postgres headless Service :5432','StatefulSet: postgres-0'])
    arrow(277,127,277,105)
    box(195,13,165,34,['postgres-data-postgres-0','1 Gi PVC / persistent volume'])
    arrow(277,66,277,47)
    box(20,131,140,34,['HPA: CPU target 50%','metrics-server supplies usage'])
    arrow(160,148,195,148,True)
    box(20,69,140,34,['VPA: recommendations','updateMode: Off'])
    arrow(160,86,195,86,True)
    d.add(String(373,147,'ConfigMap',fontSize=8,fontName='Helvetica'))
    d.add(String(373,135,'+ Secret',fontSize=8,fontName='Helvetica'))
    arrow(371,142,360,142,True)
    story.append(d)

page('User management on Kubernetes')
p('<b>Student ID: 02230135</b> | Local Kubernetes practical assignment')
p('Report prepared from observed tests on 8-9 October 2026. Eight main pages; numbered manifests follow in the appendix. Review copy: complete the submission checks on page 8 before handing in.', 'SmallNote')
heading('1. Architecture and purpose')
p('The application is a small REST API that stores names and unique email addresses in PostgreSQL. Flask handles HTTP requests, Gunicorn runs the application, and Kubernetes manages its containers. The browser currently displays JSON; a graphical form is not part of this implementation.')
architecture()
p('<b>Solid arrows:</b> request/storage relationships. <b>Dashed arrows:</b> control or configuration. Traefik and metrics-server are platform components in kube-system; the dashed boundary also contains the application namespace.', 'SmallNote')
p('The client resolves the local hostname, enters through the tunnel, and reaches Traefik. Traefik matches the Ingress rule and routes to the ready API endpoints selected by the api Service. API replicas all use the same PostgreSQL database. The PVC keeps database files independent of the Pod lifetime.')
heading('Scope')
p('This is a single-node learning environment, not a highly available database or public production service. It has no authentication, TLS or graphical frontend. The namespace separates assignment objects; it is not a complete security boundary.')

page('2. Cluster and platform | M1')
p('The minikube node uses the Docker driver on Windows with Docker Desktop in Linux-container mode. Docker inspection confirmed 2 CPUs and 4 GiB: NanoCpus=2000000000 and Memory=4294967296.')
table(['Component','Observed configuration'],[
('Kubernetes','v1.36.1; minikube node Ready'),
('Namespace','usermgmt-02230135, defined in 00-namespace.yaml'),
('Ingress controller','Traefik; ingressClassName: traefik'),
('Metrics','metrics-server Running; metric-resolution=60s'),
('StorageClass','standard (default); k8s.io/minikube-hostpath'),
('VPA platform','v1.8.0 recommender, updater and admission controller Running'),
], [130,365])
heading('Verification commands')
code('kubectl --context=minikube get nodes\nkubectl --context=minikube get pods -A\nkubectl --context=minikube get storageclass\nkubectl --context=minikube top nodes')
heading('Recorded output excerpts')
code('minikube     Ready    control-plane    v1.36.1\nstandard     k8s.io/minikube-hostpath   Delete   Immediate\nmetrics-server, traefik and all three VPA components: 1/1 Running')
p('The lines above summarize recorded outputs, rather than reproduce a terminal screenshot. Full source: evidence/M1-platform-verification.txt and evidence/M6-current-system.txt. Attach actual screenshots as required by the brief.', 'SmallNote')
heading('Platform workaround')
p('Minikube 1.39.0 stalled during startup. A checksum-verified 1.38.1 executable started the cluster; 1.39.0 supplied the Traefik add-on. The fallback warns that the selected Kubernetes version and base image are newer than its defaults. The working commands and this compatibility limitation are documented in PLATFORM-SETUP.md; they should be rehearsed on a clean cluster before submission.')
p('Commands explicitly use --context=minikube so they do not accidentally affect the separate kind cluster on this computer. Application objects are defined in k8s/ and applied using kubectl apply -f; platform components use supported add-ons/install scripts.')

page('3. Persistent PostgreSQL | M2')
p('PostgreSQL runs as one StatefulSet replica using postgres:17-alpine. The headless Service postgres supplies its stable service name. A Secret supplies database name, username and password. The manifest contains references, not the actual password.')
table(['Setting','Meaning'],[
('postgres-0','Stable Pod name provided by StatefulSet'),
('volumeClaimTemplates','Creates the per-Pod claim postgres-data-postgres-0'),
('Storage','1 Gi, ReadWriteOnce, default standard StorageClass'),
('CPU / memory requests','100m CPU and 128Mi memory'),
('CPU / memory limits','500m CPU and 512Mi memory'),
('PGDATA','/var/lib/postgresql/data/pgdata, within the mounted PVC'),
], [145,350])
heading('Persistence experiment')
p('The test created a uniquely identified row, recorded Pod and PVC identities, deleted only postgres-0, waited for its replacement to become Ready, and queried the same row. The script asserted a changed Pod UID, unchanged PVC/PV and one matching record.')
code('Before Pod UID: a908d144-f884-4808-ac50-109474622be6\nAfter Pod UID:  6cb22331-7b67-4bae-b465-7c59ad1a8930\nPVC UID:        a6742fdb-ac73-4289-8f36-6e413b1a6b44\nRow test_id:     e96e0ebe-c604-47e1-8930-e0d987683471\nRow note:       Student 02230135: saved before Pod deletion\nResult:         PASS - row survived, PVC and volume unchanged')
p('The row was queried again during report preparation and was still present. Sources: evidence/M2-persistence-test.txt and evidence/M6-persisted-row.txt. The original transcript records the SQL and assertions; the later query supplies the visible row output.', 'SmallNote')
heading('Why StatefulSet and a PVC?')
p('StatefulSet gives stable identity and a predictable claim for the database Pod. A Deployment with one PVC can also retain files, but needs careful rollout/access-mode handling and does not provide the same stable ordinal identity. Pod deletion does not delete this PVC. Namespace/PVC deletion is different: the current PV reclaim policy is Delete and can remove the backing data. Persistence here is not a backup.')

page('4. Application and health | M3')
p('The versioned image usermgmt-api:1.0 is built from app/Dockerfile and loaded into minikube. The Deployment starts two replicas; HPA later controls the replica count. Each API container requests 100m CPU/128Mi and is limited to 500m CPU/256Mi.')
table(['Endpoint','Verified behavior'],[
('GET /users','Lists stored users; 200'),('POST /users','Creates a name/email record; 201'),
('GET /users/{id}','Returns one user; 200, or 404'),('PUT /users/{id}','Updates name and email; 200, or 404'),
('DELETE /users/{id}','Deletes one user; 204, or 404'),('GET /healthz','Process liveness; does not query PostgreSQL'),
('GET /ready','Queries PostgreSQL; 200 when reachable, 503 on DB errors'),
], [145,350])
p('POST and PUT validate input. Email is normalised to lowercase and has a PostgreSQL UNIQUE constraint; duplicates return 409. Parameterised SQL separates values from SQL syntax. The init container creates the users table, using a transaction lock to coordinate simultaneous starts.')
heading('Image and configuration')
code('FROM python:3.12-slim\n# Install pinned Flask, Gunicorn and psycopg dependencies.\nUSER 10001:10001\nEXPOSE 8000\n# Gunicorn: 2 workers, 2 threads; binds 0.0.0.0:8000')
p('This is an abbreviated Dockerfile excerpt; the full file is app/Dockerfile. api-config holds DB_HOST, DB_PORT and DB_NAME; postgres-secret supplies credentials. Service api is ClusterIP, port 80 to container port 8000.', 'SmallNote')
heading('Test evidence')
p('The CRUD script verified create/read/list/update/delete, duplicate POST and PUT, invalid input, missing users and both health endpoints. It used local port 8081 because an unrelated Docker application occupied the assignment example port 8080. The README documents this substitution and how to use 8080 when free.')
p('A separate mocked outage test verified that /healthz remains 200 while /ready becomes 503. This is a unit test of endpoint behavior, not a claim that a live outage experiment was performed. Sources: evidence/M3-api-tests.txt, M3-health-test.txt and M3-deployment-verification.txt.', 'SmallNote')

page('5. Host-based routing | M4')
p('07-api-ingress.yaml uses networking.k8s.io/v1 and the installed traefik Ingress class. The host usermgmt-02230135.local and Prefix path / map to Service api on port 80.')
code('spec:\n  ingressClassName: traefik\n  rules:\n    - host: usermgmt-02230135.local\n      http:\n        paths:\n          - path: /\n            pathType: Prefix\n            backend:\n              service:\n                name: api\n                port:\n                  number: 80')
heading('Windows access')
p('The hosts file contains 127.0.0.1 usermgmt-02230135.local. A running minikube tunnel makes the controller reachable on localhost. The hosts entry handles name resolution; it does not define the Kubernetes routing rule. Windows Administrator access was needed to add the entry.')
heading('Positive and negative tests')
code('curl.exe --noproxy "*" http://usermgmt-02230135.local/users\nHTTP 200\n[{"email":"laxuman@example.com","id":4,"name":"Laxuman"}]\n\ncurl.exe --noproxy "*" -H "Host: wrong-02230135.local" `\n  http://127.0.0.1/users\nHTTP 404 - page not found')
p('These are shortened excerpts of the successful test transcript, not screenshots. The wrong-host request reaches the same controller but has no matching rule. Source: evidence/M4-ingress-tests.txt.', 'SmallNote')
heading('Request path')
p('<b>Client &gt; tunnel &gt; Traefik &gt; matching Ingress rule &gt; api Service backend &gt; ready API Pod.</b> The Ingress is configuration; the controller receives and forwards traffic. PostgreSQL is reached from the API, not directly from the browser. Visiting / gives 404 because this API defines /users, /healthz and /ready, not a homepage.')

page('6. Measured autoscaling | M5')
p('HPA targets Deployment api with autoscaling/v2, minReplicas 2, maxReplicas 6 and average CPU utilisation 50%. CPU is measured relative to each Pod\'s request: 50% of 100m is approximately 50m, not 50% of the laptop or container limit.')
story.append(Image(str(ROOT/'evidence/M5-20261009T174018Z/autoscaling.png'), width=495, height=297))
p('Figure: recorded run M5-20261009T174018Z. Blue shading marks 180 seconds of GET /users load through Ingress. Ten clients completed 6,002 HTTP 200 responses with zero errors and zero new container restarts.', 'SmallNote')
table(['Elapsed time','CPU / replica observation'],[
('0 s','2 ready Pods; baseline CPU 2%'),('90 s','5 ready Pods; reported CPU 114%'),
('180 s','Load stopped; 5 ready Pods'),('210 s','6 ready Pods after delayed load measurement'),
('540 s','3 ready Pods'),('600 s','2 ready Pods; automatic scale-down complete'),
], [105,390])
p('metrics-server samples every 60 seconds. The HPA uses a 300-second scale-down stabilisation window, explaining both the delayed last scale-up and gradual return to two Pods. Detailed evidence: timeline.csv, observations.jsonl, summary.json and hpa-describe.txt in the run directory.', 'SmallNote')

page('7. VPA and troubleshooting')
heading('Recommendations without database disruption')
p('09-postgres-vpa.yaml targets StatefulSet postgres with updateMode: Off. The recommender supplies values, while the updater does not resize or evict the Pod for this VPA. The final recorded values were:')
table(['Resource','Lower bound','Target','Upper bound'],[
('CPU','25m','25m','6336m'),('Memory','250Mi','250Mi','1121342932 bytes'),
], [85,115,115,180])
p('These are the values in the successful run\'s vpa-describe.txt. They reflect a short local observation, not a validated capacity plan. Wide upper bounds demonstrate uncertainty; no resource requests were changed to match them.')
heading('Why HPA and VPA are separate')
p('HPA changes the number of API Pods according to usage/request. An active VPA changing CPU requests on those same Pods would change that denominator, potentially causing the controllers to react to each other. Here HPA controls the API, while VPA only recommends database resources. PostgreSQL stays one replica with persistent storage.')
heading('A real failure under heavier load')
p('A first test used 50 clients for three minutes. It scaled from two to six Pods and back, but returned 5,354 HTTP 200 responses, 4,522 HTTP 502 responses and 5,876 HTTP 503 responses. It was retained as an overload test, not reported as a clean success.')
code('kubectl --context=minikube top pods -n usermgmt-02230135\n# PostgreSQL observed at 492m; configured limit 500m.\nkubectl --context=minikube get events -n usermgmt-02230135\n# /healthz timed out; liveness failures restarted API containers.\nkubectl --context=minikube logs <api-pod> -c api --previous `\n  -n usermgmt-02230135 --tail=12')
p('The observations are consistent with database saturation and queued API work delaying health checks. They do not prove CPU was the only bottleneck. Adding API Pods does not increase the single database\'s capacity. Reducing the demonstration to ten clients produced a clean run with the same limits and manifests; this does not mean the heavier-load limitation was fixed.')
p('Sources: evidence/M5-load-events.json, M5-troubleshooting.md and both timestamped M5 run directories. Further performance work could investigate connection pooling and request queuing, using measurements before changing resource allocations.', 'SmallNote')

page('8. Evidence and submission checks')
table(['Milestone','Evidence in the repository'],[
('M1','M1-platform-verification.txt; M6-current-system.txt; PLATFORM-SETUP.md'),
('M2','M2-persistence-test.txt; M6-persisted-row.txt; scripts/test-db-persistence.ps1'),
('M3','M3-api-tests.txt; M3-health-test.txt; M3-deployment-verification.txt; app/'),
('M4','M4-ingress-tests.txt; k8s/07-api-ingress.yaml'),
('M5','M5-20261009T174018Z/: timeline, chart, summary, HPA and VPA descriptions'),
], [60,435])
heading('Before submission')
p('<b>1. Screenshots:</b> the report currently includes clearly labelled command excerpts and a generated results chart. Capture the actual terminal screenshots requested for M1 and supporting evidence. DEMO-GUIDE.md lists the commands. Do not present a formatted excerpt as a screenshot.')
p('<b>2. Reproducibility:</b> a fresh-cluster, README-only rehearsal has not yet been performed. The assignment calls for it before submission. Preserve any needed database records first; deleting the namespace/PVC can remove data. This report does not claim that check passed.')
p('<b>3. Repository:</b> no remote repository URL was configured at report preparation. Add your submission link after publishing the reviewed repository. Keep the real Secret out of Git; the appendix uses a placeholder template.')
p('<b>4. Demonstration:</b> practise the ten-minute sequence and explanation questions in DEMO-GUIDE.md. The full autoscaling recording takes ten minutes by itself, so use saved evidence to explain scale-down during the timed demonstration.')
heading('References')
for title, url in [
('Kubernetes: StatefulSets','https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/'),
('Kubernetes: Ingress','https://kubernetes.io/docs/concepts/services-networking/ingress/'),
('Kubernetes: Horizontal Pod Autoscaling','https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/'),
('VPA v1.8.0: API and update modes','https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/api.md'),
('minikube: Accessing applications','https://minikube.sigs.k8s.io/docs/handbook/accessing/'),
]:
    p(f'<link href="{url}" color="#17589a">{title}</link>', 'SmallNote')
p('Implementation facts and numerical results are from local manifests and recorded evidence. External references explain component behavior. The appendix reproduces the application manifests; the password is never read by this report builder.', 'SmallNote')

safe_secret = '''apiVersion: v1
kind: Secret
metadata:
  name: postgres-secret
  namespace: usermgmt-02230135
type: Opaque
stringData:
  POSTGRES_DB: usermgmt
  POSTGRES_USER: usermgmt_admin
  POSTGRES_PASSWORD: "REPLACE_WITH_YOUR_OWN_PASSWORD"
'''
manifest_paths = sorted((ROOT/'k8s').glob('*.yaml'))
for file in manifest_paths:
    page('Appendix | ' + file.name)
    if file.name == '01-db-secret.yaml':
        p('Safe recreation template. These are example configuration values, not a dump of the live Secret. The real password is excluded.', 'SmallNote')
        code(safe_secret)
    else:
        code(file.read_text(encoding='utf-8'))

def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor('#d4dfea'))
    canvas.line(48, 40, A4[0]-48, 40)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#526078'))
    canvas.drawString(48, 27, '02230135 | Kubernetes user management | Review copy')
    label = f'{doc.page} / 8' if doc.page <= 8 else f'Appendix {doc.page-8}'
    canvas.drawRightString(A4[0]-48, 27, label)

output = OUT/'Kubernetes_UserMgmt_Report_02230135.pdf'
doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=50, leftMargin=50,
                        topMargin=42, bottomMargin=55,
                        title='Kubernetes User Management - 02230135', author='Student 02230135')
doc.build(story, onFirstPage=footer, onLaterPages=footer)
reader = PdfReader(output)
assert len(reader.pages) == 8 + len(manifest_paths), f'Unexpected page count: {len(reader.pages)}'
assert 'Appendix | 00-namespace.yaml' in reader.pages[8].extract_text()
print(f'{output}: {len(reader.pages)} pages (8 main + {len(manifest_paths)} appendix)')
