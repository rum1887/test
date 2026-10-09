# Deployment Guide — Runtime Trust Layer

## 1. Quickstart with Docker Compose

The fastest way to spin up the complete end-to-end stack locally:

```bash
# Clone and enter repo
git clone <repo-url>
cd trustme

# Copy environment template
cp .env.example .env

# Start FalkorDB, Backend API, and Web Dashboard
docker compose -f deploy/docker/docker-compose.yml up --build
```

Access the interfaces:
- **Web Console**: `http://localhost:5173`
- **FastAPI OpenAPI Docs**: `http://localhost:8000/docs`
- **FalkorDB Graph**: `localhost:6379`

---

## 2. Local Kubernetes Lab with Kind & Tetragon

For live eBPF demonstration on Linux:

```bash
# Ensure kind, docker, and kubectl are installed
./deploy/kubernetes/setup-kind.sh
```

This creates a kind cluster with debugfs and BPF mounts, applies namespace, service accounts, RBAC, workloads, and Tetragon tracing policies.

---

## 3. Free Hosting & Deployment Strategy

To make the project publicly demonstrable at zero recurring cost:

### A. Frontend on Cloudflare Pages (Free Tier)
1. Link GitHub repository to Cloudflare Pages.
2. Build settings:
   - Framework preset: `Vite`
   - Build command: `npm run build`
   - Build output directory: `dist`
   - Root directory: `apps/web`
3. Environment variable:
   - `VITE_API_BASE_URL`: `https://your-api.onrender.com` (or Railway URL)
4. SPA routing is supported via `_redirects`.

### B. Backend API on Render / Railway (Free / Hobby Tier)
1. Deploy `deploy/docker/Dockerfile.api` or use `deploy/hosting/render.yaml`.
2. Configure environment variables:
   - `FALKORDB_HOST`: FalkorDB Cloud host or Railway Redis instance
   - `FALKORDB_PORT`: `6379`
   - `RUNTIME_MODE`: `replay_synthetic`
3. **Important Free-Tier Trade-Offs**:
   - **Cold Starts**: Render free tier services spin down after 15 minutes of inactivity; the first request takes ~30-50 seconds.
   - **Ephemeral Filesystem**: Logs must be persisted in FalkorDB rather than local disk.
   - **Kernel Privileges**: eBPF sensors require `CAP_SYS_ADMIN` and kernel debugfs, which are unsupported on serverless/free PaaS. The public demo therefore uses **Replay Mode** with clear provenance labels. Genuine eBPF executes on the local Kind lab.

### C. FalkorDB Cloud
- Use FalkorDB Cloud Free Tier (`cloud.falkordb.com`) or self-host in Docker.
- Never expose unauthenticated instances: set `FALKORDB_PASSWORD`.
