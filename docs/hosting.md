You can do that. Keep everything for Konnaxion on `konnaxion.com`, and mount Abstract Wiki Architect under the path `/abstract_wiki_architect` by adding one extra location in Nginx that points to a separate process/container.

### 1. Run Abstract Wiki Architect as a separate service

Whether you use Docker or not, the idea is:

* Konnaxion Next.js: listens on `127.0.0.1:3000`
* Abstract Wiki Architect: listens on `127.0.0.1:4000` (separate container or process)

Example with Docker (adjust to your repo):

```bash
# In your Architect project folder on the VPS
docker build -t abstractwiki-architect .

# Run container, mapping its web port to 4000 on localhost
docker run -d --name abstractwiki-architect \
  -p 127.0.0.1:4000:80 \
  abstractwiki-architect
```

If you’re not using Docker, just run it directly on 4000, e.g.:

```bash
# Example for a Node/React/Next app
npm run start -- --port 4000
```

The only requirement: the Architect app must be reachable on `http://127.0.0.1:4000/`.

Ideally configure it so it knows its base URL is `/abstract_wiki_architect` (many frameworks have a “basePath” or “homepage” setting). If you don’t, it may generate links to `/` instead of `/abstract_wiki_architect`.

---

### 2. Update the Nginx config for konnaxion.com

Open your Nginx server block for `konnaxion.com`:

```bash
sudo nano /etc/nginx/sites-available/konnaxion.conf
```

You probably have something like this already:

```nginx
server {
    listen 80;
    server_name konnaxion.com www.konnaxion.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Add a new `location` **before** the generic `/` location:

```nginx
server {
    listen 80;
    server_name konnaxion.com www.konnaxion.com;

    # Abstract Wiki Architect (separate service)
    location /abstract_wiki_architect/ {
        proxy_pass http://127.0.0.1:4000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Konnaxion Next.js frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Key points:

* The `location /abstract_wiki_architect/` block comes first so Nginx sends that path to the Architect service, not to Next.js.
* `proxy_pass http://127.0.0.1:4000/;` (with a trailing `/`) keeps the rest of the path after `/abstract_wiki_architect/` when forwarding.

Then reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

If you already have HTTPS via Certbot, this change goes in the `server { listen 443 ssl; ... }` block instead (or in both 80 and 443, depending on how Certbot configured it).

---

### 3. What you get

* `https://konnaxion.com/` → Next.js app (Konnaxion).
* `https://konnaxion.com/abstract_wiki_architect` (and everything under that) → separate Abstract Wiki Architect container/service on port 4000.

No extra DNS records needed, because this is all under the same domain and handled by Nginx via path-based routing.
