# Streamlit static image cache

Canonical artwork lives under `assets/`. The `load_local_image_url()`
helper copies requested images to `static/assets/` on first use, then
returns a same-origin `/app/static/assets/...` URL.

Only this README is committed under `static/`. Runtime copies are ignored
by Git and regenerated on demand after deployment or restart.

Static serving is enabled by `.streamlit/config.toml`. The loader falls
back to the original Base64 data URI when static serving is disabled or the
runtime folder cannot be written.
