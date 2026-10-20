.PHONY: test test-contracts test-frontend gen dev-frontend diagrams

test: test-contracts test-frontend

contracts/node_modules: contracts/package-lock.json
	cd contracts && npm ci --no-fund --no-audit
	touch $@

frontend/node_modules: frontend/package-lock.json
	cd frontend && npm ci --no-fund --no-audit
	touch $@

# Compiles every schema, checks the scripted runs in contracts/ws/examples/,
# and fails if the generated TypeScript types are stale.
test-contracts: contracts/node_modules
	cd contracts && npm test --silent

# Angular unit and component tests, driven by the scripted runs.
test-frontend: frontend/node_modules
	cd frontend && npx ng test --watch=false

# Regenerates types from contracts/. Python joins when the backend exists.
gen: contracts/node_modules
	cd contracts && npm run gen --silent

# The UI against the scripted runs: http://localhost:4200, ?mock=<script>&speed=<n>.
dev-frontend: frontend/node_modules
	cd frontend && npx ng serve

# Re-renders docs/diagrams/*.mmd to PNG. Needs a Chrome that Puppeteer can find.
diagrams:
	for f in docs/diagrams/*.mmd; do \
		npx -y @mermaid-js/mermaid-cli@11.4.2 -i $$f -o $${f%.mmd}.png -b white -s 2; \
	done
