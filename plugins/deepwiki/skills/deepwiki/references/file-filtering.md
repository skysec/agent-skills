# File Filtering Reference

This document defines which files to include or exclude when walking a repository for wiki generation.

## Include

### Source Code
| Extension | Languages |
|-----------|-----------|
| `.py` | Python |
| `.js`, `.mjs`, `.cjs` | JavaScript |
| `.ts`, `.mts`, `.cts` | TypeScript |
| `.jsx`, `.tsx` | React |
| `.go` | Go |
| `.rs` | Rust |
| `.java` | Java |
| `.kt`, `.kts` | Kotlin |
| `.swift` | Swift |
| `.rb` | Ruby |
| `.c`, `.h`, `.cpp`, `.hpp`, `.cc` | C/C++ |
| `.cs` | C# |
| `.php` | PHP |
| `.scala` | Scala |
| `.ex`, `.exs` | Elixir |
| `.clj`, `.cljs` | Clojure |
| `.hs` | Haskell |
| `.lua` | Lua |
| `.r`, `.R` | R |
| `.jl` | Julia |
| `.sh`, `.bash`, `.zsh` | Shell scripts |

### Documentation
| Extension | Type |
|-----------|------|
| `.md`, `.mdx` | Markdown |
| `.rst` | reStructuredText |
| `.txt` | Plain text (if in `docs/`) |
| `.adoc`, `.asciidoc` | AsciiDoc |

### Project Manifests & Config
| File | Purpose |
|------|---------|
| `package.json` | Node.js project |
| `pyproject.toml`, `setup.py`, `setup.cfg` | Python project |
| `Cargo.toml` | Rust project |
| `go.mod`, `go.sum` | Go project |
| `pom.xml`, `build.gradle`, `build.gradle.kts` | JVM project |
| `Gemfile` | Ruby project |
| `Makefile`, `CMakeLists.txt` | Build system |
| `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml` | Container config |
| `.env.example`, `.env.sample` | Environment reference (never `.env` itself) |
| `*.yaml`, `*.yml` | Config files (in project root or `config/`) |
| `*.toml` | Config files |
| `*.json` | Config files (not `package-lock.json` or similar) |

## Exclude

### Dependency directories
```
node_modules/
vendor/
.venv/
venv/
env/
__pypackages__/
.bundle/
bower_components/
jspm_packages/
```

### Build output
```
dist/
build/
out/
target/
.next/
.nuxt/
.svelte-kit/
__pycache__/
*.pyc
*.pyo
.class files
```

### Lock files (too noisy, no semantic value)
```
package-lock.json
yarn.lock
pnpm-lock.yaml
Gemfile.lock
Cargo.lock  (include in application repos, exclude in library repos)
poetry.lock
uv.lock
composer.lock
```

### Generated / minified files
```
*.min.js
*.min.css
*.bundle.js
*.chunk.js
```

### Version control & IDE metadata
```
.git/
.svn/
.hg/
.idea/
.vscode/
*.suo
*.user
```

### Binary and media assets
```
*.png, *.jpg, *.jpeg, *.gif, *.webp, *.svg (if in assets/ — keep if in docs/)
*.mp4, *.mp3, *.mov
*.woff, *.woff2, *.ttf, *.eot
*.pdf (unless explicitly asked about)
*.zip, *.tar.gz, *.tgz
*.exe, *.dll, *.so, *.dylib
```

### Test fixtures and sample data
```
fixtures/
__fixtures__/
testdata/
test/data/
spec/fixtures/
*.fixture.json  (if >50 lines)
*.snapshot  (Jest snapshots)
```

### Coverage and CI artifacts
```
coverage/
.nyc_output/
.cache/
.pytest_cache/
htmlcov/
```

## Prioritization Strategy

When a repo is large (>200 relevant files), prioritize:

1. **Entry points**: `main.*`, `index.*`, `app.*`, `server.*`, `cmd/`
2. **Core modules**: the top-level packages/directories with the most imports
3. **Public API surface**: exported functions, REST handlers, GraphQL resolvers
4. **Configuration**: how the system is configured and what options exist
5. **Tests** (for understanding expected behavior): `*_test.go`, `*.test.ts`, `*_spec.rb`

For pages covering a specific component, `filePaths` should include only the files most directly relevant — typically 3–8 files. Loading too many files at once dilutes the context and produces generic output.
