# Autoscaling load-test observations

## Initial 50-client stress test

Run directory: `M5-20261009T173013Z`.

- Requests went through `http://usermgmt-02230135.local/users`, not the direct API port-forward.
- The baseline was two API Pods. At the 90-second sample the HPA reported 248% average CPU utilisation against a 50% target and six ready API Pods.
- `kubectl --context=minikube top pods -n usermgmt-02230135` showed PostgreSQL at 492m CPU while its configured CPU limit was 500m.
- `kubectl --context=minikube get events -n usermgmt-02230135 --sort-by=.lastTimestamp` showed HTTP health-check timeouts and liveness-triggered API container restarts. A raw event snapshot is in `M5-load-events.json`.
- PostgreSQL did not restart. The API containers became ready again after load stopped.

Interpretation: the measurements are consistent with database saturation and queued API requests delaying probes. This is an inference, not proof that CPU was the only bottleneck. The API opens a database connection for each request, so increasing API replica count does not remove the shared database bottleneck. Successful autoscaling alone is not proof that every request succeeded.

The follow-up demonstration uses ten concurrent clients on the same `/users` endpoint. The manifests and resource limits are unchanged. The test script records HTTP errors and new container restarts as well as replica counts, and only reports a clean pass when all of these checks succeed. The heavier run is retained as stress-test evidence rather than discarded.

The initial empty `M5-20261009T173007Z` run ended before generating load because the recorder did not handle the HPA's initially null metrics list. The recorder was corrected to treat that value as metrics not yet available.

## Successful ten-client demonstration

Run directory: `M5-20261009T174018Z`, starting at 17:40:19 UTC on 9 October 2026.

- 180 seconds of load followed by 420 seconds of observation; samples every 30 seconds.
- 6,002 HTTP 200 responses; no failed requests and no new API container restarts.
- Observed replica sequence: 2 → 5 → 6 → 3 → 2. Two Pods were ready at the end.
- Five Pods were ready at the 90-second sample. Six were observed at 210 seconds, shortly after the load ended, because metrics lagged behind traffic. Three were observed at 540 seconds, and two at 600 seconds.
- The installed metrics-server uses `--metric-resolution=60s`. The HPA's scale-down stabilisation window is 300 seconds. Both contribute to delayed scaling decisions.
- VPA remained `Off` and reported CPU/memory lower bounds, targets and upper bounds. Its target at the end was 25m CPU and 250Mi memory. The wide upper bounds and brief observation history mean these values should not be treated as proven production sizing.
- The saved user record remained reachable through Ingress after scale-down.

Use this run's `timeline.csv`, `autoscaling.png`, `summary.json`, `hpa-describe.txt` and `vpa-describe.txt` as the main milestone 5 evidence. Use the first run and the event snapshot to discuss overload and troubleshooting. No resource limits were changed between runs.
