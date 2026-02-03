# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0](https://github.com/etalab-ia/rag-facile/compare/v0.2.0...v0.3.0) (2026-02-03)


### Features

* Add Albert API integration and update project documentation for simplified setup with `just` commands. ([5ba73a3](https://github.com/etalab-ia/rag-facile/commit/5ba73a33373dff8645a8108e7241a771cb5e08ef))
* add bootstrap installer and auto-download templates ([66a2015](https://github.com/etalab-ia/rag-facile/commit/66a2015ab374cd607d1b098db800d7479d91dcd3))
* add bootstrap installer and bundle templates in CLI ([c876a4e](https://github.com/etalab-ia/rag-facile/commit/c876a4e935d5072d4485dae4a50547cf8a81bc11))
* add chainlit-chat template and generator ([abfb788](https://github.com/etalab-ia/rag-facile/commit/abfb788876b3086b87b76926b76d91a83a1a10e5))
* Add default recipe to justfiles to display help ([eb27ecf](https://github.com/etalab-ia/rag-facile/commit/eb27ecf873dfb6adbbe95898486dddda5baa412c))
* add direnv configuration ([b5cb2a7](https://github.com/etalab-ia/rag-facile/commit/b5cb2a72148f682448b5332da6a1abd061aeaba6))
* add direnv configuration and remove .envrc from gitignore. ([d2df794](https://github.com/etalab-ia/rag-facile/commit/d2df7944fe439eb1c667b3000ab4e5e23fd0c073))
* add gritql template generation for chainlit-chat ([0075244](https://github.com/etalab-ia/rag-facile/commit/00752442b59e38743ff02ea64de5811608c6a8c1))
* add just commands for template generation and instantiation ([1f2619d](https://github.com/etalab-ia/rag-facile/commit/1f2619db30dc1a29f665b5b5950e5544f9966d53))
* add justfile to run reflex-chat ([a1ac644](https://github.com/etalab-ia/rag-facile/commit/a1ac644fb18dc0b3df9c396a03e8053ea7289255))
* add moon tasks, Justfile, and CONTRIBUTING.md ([0d07041](https://github.com/etalab-ia/rag-facile/commit/0d07041a0d73c86281cb0007eb86b91e9ea4d4f2))
* add reflex-chat app and downgrade to Python 3.13 ([7395391](https://github.com/etalab-ia/rag-facile/commit/7395391aeab4acc28494cd3c4a79b0f2c19c1b00))
* add reflex-chat application and Albert API integration ([aa8be55](https://github.com/etalab-ia/rag-facile/commit/aa8be55eca1b8ccd58d91cd5eec7269e479ab9ba))
* Add script to automatically open browser to localhost:3000 and integrate it into the `dev` task in `moon.yml`. ([1858c6a](https://github.com/etalab-ia/rag-facile/commit/1858c6a328d76975ec04c385d09a0a023e43a1d9))
* auto-install proto and moon if not present ([4aea431](https://github.com/etalab-ia/rag-facile/commit/4aea4316944822b3f63de46992d4684313b1edb9))
* auto-run uv sync and start dev server after generation ([92d0090](https://github.com/etalab-ia/rag-facile/commit/92d00901e2d66ee1e903861ce3c6552afd8fc531))
* bundle templates in CLI package distribution ([6408718](https://github.com/etalab-ia/rag-facile/commit/6408718d8902f0c13684e5d88ff229898758e19d))
* complete rf generate workspace command ([06a7cae](https://github.com/etalab-ia/rag-facile/commit/06a7cae9bbea65f4bedbf475ba8b9049b087721c))
* Enhance `create-app` justfile recipe to normalize app type inputs and support shorthands. ([ccc40b8](https://github.com/etalab-ia/rag-facile/commit/ccc40b856e3d301bde9479f8fd8cc5db45385749))
* extract pdf-context package and fix templates ([9cac265](https://github.com/etalab-ia/rag-facile/commit/9cac2657e3d441ab7f5c6dc9e98b545f90fce527))
* extract pdf-context package and fix templates ([fd021ee](https://github.com/etalab-ia/rag-facile/commit/fd021eeef2d283996e58c730a8af705ead5d8886))
* generalize hybrid codemod pipeline to support multiple apps ([4dfff91](https://github.com/etalab-ia/rag-facile/commit/4dfff914cb65adb44cdfb57126577e0a5bb90056))
* implement chainlit-chat and project cleanup ([5d34133](https://github.com/etalab-ia/rag-facile/commit/5d341334b5779f7315eab362b48551345b61a87e))
* implement chainlit-chat app, update AGENTS.md, and rename project to rag-facile ([afe1d9c](https://github.com/etalab-ia/rag-facile/commit/afe1d9c4b17d488929d78b388719e337cb531676))
* implement hybrid Factory + Tera architecture for modular template generation ([fb8e0db](https://github.com/etalab-ia/rag-facile/commit/fb8e0db7d6cbeb4be3006dcc2e7ad82db7d42ef4))
* implement hybrid LibCST + ast-grep pipeline for chainlit-chat ([6634c86](https://github.com/etalab-ia/rag-facile/commit/6634c86c9f59813ee14f9d922d47bc0db29842e3))
* implement hybrid LibCST + ast-grep pipeline for template generation ([ba385ba](https://github.com/etalab-ia/rag-facile/commit/ba385ba275932dc158f504b684ed47931b5eb8cf))
* implement Init + Patch architecture for workspace generation ([7d8ff6a](https://github.com/etalab-ia/rag-facile/commit/7d8ff6a5cfe4e9c144dc5404d78b1300792f4d5f))
* Implement PDF upload and context integration for the Reflex chat application. ([492b051](https://github.com/etalab-ia/rag-facile/commit/492b0515ca08caa43aaf85bd1d525fbbe03f1942))
* Implement UI for displaying attached files in the chat input and refine the action bar's styling and layout. ([16b6318](https://github.com/etalab-ia/rag-facile/commit/16b63188fe9af9d53441e6a2bd50501892e9dfc8))
* Initial RAG starter kit setup ([80ce74e](https://github.com/etalab-ia/rag-facile/commit/80ce74ea33d62580b2fd6edb46d56ba65b62db66))
* Initial setup of RAG starter kit (v0.1.0) ([6135ebb](https://github.com/etalab-ia/rag-facile/commit/6135ebb283fa0c3baf3fe23bf4fbc1a72a45b42c))
* integrate release-please for unified monorepo versioning ([e703ff1](https://github.com/etalab-ia/rag-facile/commit/e703ff18e7710fa12e9e48c1b8f9e01cfc7e35b3))
* integrate release-please for unified monorepo versioning ([89cc602](https://github.com/etalab-ia/rag-facile/commit/89cc60278f2da72fed737bff0cfeec3299e33a48))
* make CLI installable via uv tool install ([27db58a](https://github.com/etalab-ia/rag-facile/commit/27db58a871f0cff1da0c8b8a19840c4eea5333bd))
* make CLI installable via uv tool install ([63ec4ab](https://github.com/etalab-ia/rag-facile/commit/63ec4ab2cb4a993c6b9914db098ce03e0eb0867c))
* parameterize env vars and fix grit usage ([72be38a](https://github.com/etalab-ia/rag-facile/commit/72be38a8723e2295f1697fe4842be0469488cfa0))
* prompt for env config and create .env file during generation ([6219006](https://github.com/etalab-ia/rag-facile/commit/62190067ad9df600b3997b1e3f9bcc83e4bce688))
* refactor template generation cli for multi-app support ([88990d2](https://github.com/etalab-ia/rag-facile/commit/88990d2c0bfccfbe2aa57b4438f01dce29d58d2f))
* **reflex-chat:** Add PDF Context Support and Refined UI ([13c51f5](https://github.com/etalab-ia/rag-facile/commit/13c51f5678083aada30bd242651202ed4d7bcd90))
* **reflex-chat:** add python-dotenv for .env file loading ([7c49d0d](https://github.com/etalab-ia/rag-facile/commit/7c49d0d63e665671e2816148ec011c995704ec25))
* rename CLI to rag-facile and add ASCII banner ([01a0165](https://github.com/etalab-ia/rag-facile/commit/01a01656fc140f8a4be1b21dcf8166eddb2730d9))
* rename CLI to rag-facile and add ASCII banner ([fdf917b](https://github.com/etalab-ia/rag-facile/commit/fdf917b5d51c5ab42b8365015bcc29031c624008))
* rf generate workspace - one command to running RAG app ([d520536](https://github.com/etalab-ia/rag-facile/commit/d520536882b34ab853cf2d43da028b05b71df192))
* support RAG_FACILE_BRANCH env var in install.sh ([215ff5a](https://github.com/etalab-ia/rag-facile/commit/215ff5af47896836056954ba6b82a0c9ca998ddf))
* support reflex-chat in template generation CLI ([06040e1](https://github.com/etalab-ia/rag-facile/commit/06040e1cb891c786ae32c6de695653320d5b8ff5))
* **templates:** support env var API keys and fix uv sync warning ([a26a598](https://github.com/etalab-ia/rag-facile/commit/a26a59862c7bedd95840673ecb800fdc9e771b95))
* **templates:** update reflex-chat template with parameterized imports and jinja extensions ([cb8ec7f](https://github.com/etalab-ia/rag-facile/commit/cb8ec7f6cbfd95934439472cfc0b0f98ee97e4e5))
* update default OpenAI API key help message, base URL, and model to Albert API endpoints. ([519e96f](https://github.com/etalab-ia/rag-facile/commit/519e96f4033cfc656e314d04fb392c210bb83521))


### Bug Fixes

* Add `ty:ignore[call-non-callable]` comments to suppress type errors in `navbar.py` and `state.py`. ([e33b488](https://github.com/etalab-ia/rag-facile/commit/e33b488b1ad21cdd3e35ac72f33fd0b54b91f7ab))
* add proto paths to PATH after installation ([6a289ff](https://github.com/etalab-ia/rag-facile/commit/6a289ff1db79522aa3e607c2f6dc265fac848f3f))
* Add ruff and ty exclusions for template directories ([198a77e](https://github.com/etalab-ia/rag-facile/commit/198a77e77f1ad2ce919eb860335fb4a488d2f19c))
* Add unzip as a system dependency for Reflex ([bfed9fb](https://github.com/etalab-ia/rag-facile/commit/bfed9fb6990211fb6543637e45300036b70bddfc))
* add validation to create-app just command ([7ad5bbc](https://github.com/etalab-ia/rag-facile/commit/7ad5bbcc6bf6e4358e4a4560b33580c0ff0a2e88))
* Address PR review feedback (Python 3.14.2, ruff 0.9.3, rag-facile) ([b6c8ea0](https://github.com/etalab-ia/rag-facile/commit/b6c8ea02afacbed63e1d68971a22f59b0418c517))
* **cli:** rename main app file and parameterize imports in reflex template ([c95823d](https://github.com/etalab-ia/rag-facile/commit/c95823d9400b5de0a25b6a42efdeef2e9061cb39))
* configure ty excludes in pyproject.toml ([89641fa](https://github.com/etalab-ia/rag-facile/commit/89641fa4ab11ea72e2a5281d8dc5f7076b7882ca))
* configure ty to handle metaprogramming false positives ([41f7e3d](https://github.com/etalab-ia/rag-facile/commit/41f7e3db1f698cf59850d69996e746c3ecad693b))
* exclude template directories from ruff checks ([730ea37](https://github.com/etalab-ia/rag-facile/commit/730ea37a4b9303ba47dfe1dca0f84539543bf0a2))
* fix test mocks for workspace generation flow ([bab1fbb](https://github.com/etalab-ia/rag-facile/commit/bab1fbb2a6167dfdb9a40be476ad4fc6ceedf5f2))
* increase engineio max_decode_packets to prevent payload errors ([a9b4a6b](https://github.com/etalab-ia/rag-facile/commit/a9b4a6b81423c78104485372ac46d93d4bbd2dad))
* Install just in install.sh and update docs ([2643b08](https://github.com/etalab-ia/rag-facile/commit/2643b0852ce1ca1be7e2ddd11c00c82ffa681a84))
* parameterize imports and add dotenv loading for reflex-chat ([fa7720f](https://github.com/etalab-ia/rag-facile/commit/fa7720f8b51f88a653e96c216b6d5cced5c8eedd))
* Prevent potential errors by checking if `item.choices` is valid before accessing its elements. ([371ddbc](https://github.com/etalab-ia/rag-facile/commit/371ddbc61cd512c203863609131fd3e093adeb53))
* Properly escape Just variables in justfile template ([9bf4c52](https://github.com/etalab-ia/rag-facile/commit/9bf4c5206051a30ade18f7e2919e1fcc97d12875))
* rename README.md to .jinja for full parameterization ([d4e4a66](https://github.com/etalab-ia/rag-facile/commit/d4e4a66ca51861f5b527c2eebc1f652d8faa902a))
* resolve ast-grep warnings and improve reflex parameterization ([59acb4b](https://github.com/etalab-ia/rag-facile/commit/59acb4b17620595427d1ea8aaf068162607e50a1))
* resolve IndexError in streaming and add PDF processing support ([42414ce](https://github.com/etalab-ia/rag-facile/commit/42414ce1311d51674dd25616dd21074650829104))
* resolve linting and formatting issues ([ecf8e84](https://github.com/etalab-ia/rag-facile/commit/ecf8e844fda2449a89cabdc8056f7f1bdb4721ac))
* resolve type error in chainlit app ([505dde9](https://github.com/etalab-ia/rag-facile/commit/505dde9cb4ff596c4b032c55312a4f307c496b2d))
* restrict python version to 3.13 for pydantic compatibility ([0657255](https://github.com/etalab-ia/rag-facile/commit/0657255f39ad7f2e0e2c9368b30e7cf1a937224d))
* set default just task to list commands ([c668c37](https://github.com/etalab-ia/rag-facile/commit/c668c3795b3e4b7aa908735bc7192e19e82928b0))
* update release-please-config.json ([4250615](https://github.com/etalab-ia/rag-facile/commit/42506157595889fd140d5ee068368b4644dc7b18))
* use --exclude flag for ty (exclude not valid in config) ([2e917bc](https://github.com/etalab-ia/rag-facile/commit/2e917bc8c1d41c9036f2c122ab43ae2f2081b57e))
* use --yes flag for proto install to avoid interactive prompt issues ([07f9d63](https://github.com/etalab-ia/rag-facile/commit/07f9d632780b5fc3e8835404aa2739f49a801234))
* use .jinja extension for parameterized template files ([d44f573](https://github.com/etalab-ia/rag-facile/commit/d44f573f78c3ea1cbc30d20767ebb1eae5ffcdcd))
* Use Just variable syntax in run recipe ([eddff73](https://github.com/etalab-ia/rag-facile/commit/eddff7311bcde42654cd69341398fd316db29f0e))
* use moonrepo/setup-toolchain action and pin Python 3.13 ([1deafc1](https://github.com/etalab-ia/rag-facile/commit/1deafc1f68575f627fa885350d7ff2149677b2a6))
* Use shell variable syntax in justfile to avoid Tera conflicts ([7e986ef](https://github.com/etalab-ia/rag-facile/commit/7e986ef3031096cdeb3467af6410664571b0e1dc))


### Documentation

* Add AGENTS.md with project knowledge ([e96ccb7](https://github.com/etalab-ia/rag-facile/commit/e96ccb79a17f3144f852be71db01936084bdee0d))
* Add AGENTS.md with project knowledge ([a2c8beb](https://github.com/etalab-ia/rag-facile/commit/a2c8beb379fd82d83cfe8d9e4989b182d300c39f))
* add CHANGELOG from merged PR history ([16bf483](https://github.com/etalab-ia/rag-facile/commit/16bf483a8642854b927b915ae146960dfb723821))
* add Docker testing instructions to CONTRIBUTING.md ([2ef49ff](https://github.com/etalab-ia/rag-facile/commit/2ef49ff593069784f9db7cfe40dbce4a9edec8f0))
* add proto prerequisites to README ([6ea9e2c](https://github.com/etalab-ia/rag-facile/commit/6ea9e2c049756b051767f75b5db2222e92219885))
* add template generation instructions to root README ([26d2e00](https://github.com/etalab-ia/rag-facile/commit/26d2e00ff1a49273c32ef63c081322175ee7d387))
* clarify available vs planned application templates ([d3f5bd8](https://github.com/etalab-ia/rag-facile/commit/d3f5bd8361fffc31e324b53273ff83f51a51f67b))
* clarify available vs planned application templates in README ([a6f6c96](https://github.com/etalab-ia/rag-facile/commit/a6f6c963f0277aecf45b3598b0d0e4ea96bc043f))
* Document justfile commands in README ([9fd7211](https://github.com/etalab-ia/rag-facile/commit/9fd721193ec9faad2dd2b1649b7d7ceea0dddeac))
* document RAG_FACILE_BRANCH for testing from branches ([d6a25f3](https://github.com/etalab-ia/rag-facile/commit/d6a25f3fd96754c6173d9f12930e6c2b5729e375))
* improve template READMEs for standalone use and add CLI README ([c511de2](https://github.com/etalab-ia/rag-facile/commit/c511de2f142054ff2f94c5b347082bf899e6b6f2))
* update app and template READMEs with just command instructions ([c2d5ca6](https://github.com/etalab-ia/rag-facile/commit/c2d5ca629213e64ab72a293124ec474a60645b70))
* Update install.sh examples to use pipe syntax ([9309c27](https://github.com/etalab-ia/rag-facile/commit/9309c27eb96a776f6ad6acc5d2e589cd303e98bc))
* update README and CONTRIBUTING with architecture overview ([2f1fd99](https://github.com/etalab-ia/rag-facile/commit/2f1fd99bdd6a5b30099d2f096e28f420d8408085))
* Update README with correct run command syntax ([b071f52](https://github.com/etalab-ia/rag-facile/commit/b071f529f56bfc19b442857a2f60cbf11e84d570))
* update README with simplified install instructions ([6a7c4f8](https://github.com/etalab-ia/rag-facile/commit/6a7c4f8b38138565a615a716769ca8aab5b6f41a))
* update README with template management and usage instructions ([2a93250](https://github.com/etalab-ia/rag-facile/commit/2a9325022490873ec36b617803de03db2c0c75ac))
* update root README to reflect the change from apps/chat to apps/chainlit-chat ([7bd4106](https://github.com/etalab-ia/rag-facile/commit/7bd4106c2d39255355cd63ffa3dd4d161b8353fa))

## [Unreleased]

## [0.1.0] - 2026-02-03

### Added

- **CLI Enhancements** (#18, #17)
  - Rename CLI to `rag-facile` for consistency
  - Add ASCII banner on CLI startup for better UX
  - Add Justfile for generated projects to simplify common tasks
  - Make CLI installable via `uv tool install` for easy distribution

- **Bootstrap Installer** (#16)
  - Create comprehensive bootstrap installer (`install.sh`)
  - Bundle templates into CLI at build time for zero-dependency deployment
  - Support for system prerequisites auto-installation on Debian/Ubuntu

- **Template System Overhaul** (#14, #7)
  - Refactor from simple string templates to Moon codegen for production-grade template handling
  - Implement hybrid LibCST + ast-grep pipeline for intelligent code transformation
  - Support code-aware template generation for Python and other languages

- **Application Templates** (#5, #6)
  - Add `chainlit-chat` template with Grit-based code generation
  - Add support for `reflex-chat` in template generation CLI
  - Enable template generation CLI to scaffold multiple app types

- **Core Applications** (#4, #3)
  - Implement `chainlit-chat` application with Albert API integration
  - Add `reflex-chat` application with Albert API support
  - Integrate PDF context support in reflex-chat for document-aware RAG

- **PDF Context Package** (#12, #13)
  - Extract PDF context handling into reusable `pdf-context` package
  - Add PDF context support to reflex-chat application
  - Implement refined UI for PDF interaction

- **Workspace Generation** (#15)
  - Create `rf generate` command for one-command workspace scaffolding
  - Enable rapid project initialization with all necessary boilerplate

- **Development Tools & Documentation** (#8, #9, #10, #11, #2)
  - Add direnv configuration for automatic environment setup
  - Separate user-facing and contributor documentation
  - Add AGENTS.md with comprehensive project knowledge
  - Clarify available vs planned application templates in README

### Initial Release

- Project setup with monorepo structure using moonrepo and uv
- Foundation for multi-app RAG framework targeting French government use cases
- Python 3.13+ codebase with ruff (linting/formatting) and ty (type checking)
- Extensible template system for scaffolding new applications

---

## How to Read This Changelog

- **Added**: New features and capabilities
- **Changed**: Modifications to existing features
- **Fixed**: Bug fixes
- **Deprecated**: Features marked for future removal
- **Removed**: Features that have been removed
- **Security**: Security-related fixes

## Release History

| Version | Date | Notes |
|---------|------|-------|
| 0.1.0 | 2026-02-03 | Initial release with core RAG framework and applications |
