# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0](https://github.com/etalab-ia/rag-facile/compare/v0.7.0...v0.8.0) (2026-02-09)


### Features

* Add Albert Client SDK - Complete Python SDK for Albert API ([ebf3d55](https://github.com/etalab-ia/rag-facile/commit/ebf3d55fa603cf1f9fcfed0024dae6f646080d0f))
* add albert-client package template for monorepo workspaces ([1e99698](https://github.com/etalab-ia/rag-facile/commit/1e9969868d0c3228cef8d04b76cd2e1c3975048f))
* add albert-client SDK Phase 1 (core client + OpenAI passthrough) ([0424d2c](https://github.com/etalab-ia/rag-facile/commit/0424d2c1b8adf9f0eb6bcb9d3a2fcc35f28da5a1))
* add OPENAI_API_KEY fallback for AlbertClient initialization ([418b5f2](https://github.com/etalab-ia/rag-facile/commit/418b5f233d3432ea8d331ec0a3c9158d589fe5f9))
* implement Phase 2 (Search + Rerank) for Albert Client SDK ([675ad56](https://github.com/etalab-ia/rag-facile/commit/675ad56815574b385edd42042f379d84740ec592))
* implement Phase 3 (Collections & Documents) for Albert Client SDK ([f7d29af](https://github.com/etalab-ia/rag-facile/commit/f7d29af15ae09bc1b5be3402331d382641a0b41a))
* implement Phase 4 (Tools & Monitoring) for Albert Client SDK ([4b0abba](https://github.com/etalab-ia/rag-facile/commit/4b0abba2fe3cd0e0d6433f3915f31bd38ebe36d3))


### Bug Fixes

* add albert-client to workspace dependencies and test dependencies ([8d405f8](https://github.com/etalab-ia/rag-facile/commit/8d405f8c4ef54915350ba87a4792475567e1b710))
* bundle albert-client with CLI for standalone workspaces ([d36c744](https://github.com/etalab-ia/rag-facile/commit/d36c7445e64ee5fa06f4a1e7252042f306a980ea))
* centralize ruff config and remove unused resources directory ([552d071](https://github.com/etalab-ia/rag-facile/commit/552d07105c097ce881e83b0946f1db2ef2ebb13f))
* correct API usage in documentation examples ([122beaa](https://github.com/etalab-ia/rag-facile/commit/122beaaaee26265b58643682c6b11fdb61fc34ca))
* regenerate templates with albert-client dependency ([094be96](https://github.com/etalab-ia/rag-facile/commit/094be96021a8c1e5e9fffd5f43a569af7b0c1d78))
* rename app.py to match Reflex app_name requirement in standalone workspaces ([9c20691](https://github.com/etalab-ia/rag-facile/commit/9c2069187bbe548128487198a093aa2757df31c6))
* use correct Albert API model aliases in documentation ([a9fcd03](https://github.com/etalab-ia/rag-facile/commit/a9fcd035e851f307a3576d04802cce1a28c85dca))


### Documentation

* add Albert Client SDK documentation ([eeb5d8d](https://github.com/etalab-ia/rag-facile/commit/eeb5d8d7332910812e10bc0862f4fecbd0eb7436))
* add Albert Client SDK with audience-focused documentation ([6a3a51e](https://github.com/etalab-ia/rag-facile/commit/6a3a51e7e3c8126ca34ed08ec4054cded5ead16b))
* improve type safety documentation in albert-client SDK ([dc7d2af](https://github.com/etalab-ia/rag-facile/commit/dc7d2afddf9de71b5fb289d5e6b453a93f6c299d))

## [0.7.0](https://github.com/etalab-ia/rag-facile/compare/v0.6.1...v0.7.0) (2026-02-07)


### Features

* add --version flag to rag-facile CLI ([daadefe](https://github.com/etalab-ia/rag-facile/commit/daadefe020b6f06c0dd9f166540d82ee16a3c5c3))
* add just sync task to install dependencies and pre-commit hooks ([2e5dd71](https://github.com/etalab-ia/rag-facile/commit/2e5dd71ef385bc7ad87d4b665c27db2c69b2d5bb))
* add proxy support to install script for corporate/restricted networks ([0a90cc3](https://github.com/etalab-ia/rag-facile/commit/0a90cc305b1747183b0dac12aa8f169008f54626))
* add Windows support with proto as unified dependency manager ([5c0ee40](https://github.com/etalab-ia/rag-facile/commit/5c0ee403200d52ad1909d0c2e50fc565ea2ab56f))
* add Windows support with proto as unified dependency manager ([6cd5300](https://github.com/etalab-ia/rag-facile/commit/6cd5300f3fee0362314f9e1c9b555e3279c90f04))


### Bug Fixes

* add .prototools to workspace templates and pin Python 3.13.11 ([0df9943](https://github.com/etalab-ia/rag-facile/commit/0df99431bc71aadcb7be5fb5caeac55ea8c0459d))
* add comprehensive error handling for SSL certificate issues in proto installation ([75522f9](https://github.com/etalab-ia/rag-facile/commit/75522f967279d16f0ff216e22d2a066af88e6e2f))
* add explicit permissions block to test-install workflow ([be62466](https://github.com/etalab-ia/rag-facile/commit/be624666be8f455232865c2280ae2a19dfdc83d7))
* add fallback curl without SSL verification for corporate proxies ([6bc2e7e](https://github.com/etalab-ia/rag-facile/commit/6bc2e7e104846a0be045d05c0607a5e869fb8649))
* add proto paths to GITHUB_PATH and force UTF-8 encoding on Windows ([a84d042](https://github.com/etalab-ia/rag-facile/commit/a84d0429a205c92a89deaa6c6f51a8facb0cebca))
* add uv tools directory to PATH on Windows ([6a3654e](https://github.com/etalab-ia/rag-facile/commit/6a3654e3fd6c60abd32bdb9e5fd65265380050d8))
* add verbose output and error logging to installer tests ([1c1c0e3](https://github.com/etalab-ia/rag-facile/commit/1c1c0e305b5b28ce46581aea1ce6abe6cd395bd4))
* address review feedback on PR [#53](https://github.com/etalab-ia/rag-facile/issues/53) ([78e0710](https://github.com/etalab-ia/rag-facile/commit/78e07105190fd3b3c8ec39969cb1ff223fbbfb0f))
* address review feedback on PR [#54](https://github.com/etalab-ia/rag-facile/issues/54) ([0be49f8](https://github.com/etalab-ia/rag-facile/commit/0be49f8222dd06038f8b6d983d0bb8647d9f0e06))
* catch all exceptions when printing CLI banner ([8b0ed8b](https://github.com/etalab-ia/rag-facile/commit/8b0ed8bb16c0f151861888f57d8a121bb6ee86d9))
* correct just plugin URL from moonrepo to Phault repository ([24e06af](https://github.com/etalab-ia/rag-facile/commit/24e06afc4dc953f498f3efb68ced26717c6bab7d))
* export PATH to GitHub Actions environment for CI/CD ([eadf6b3](https://github.com/etalab-ia/rag-facile/commit/eadf6b32d92335f0a35580067de07a3244fa291d))
* handle Windows encoding issues in CI and CLI ([e672345](https://github.com/etalab-ia/rag-facile/commit/e672345e2a03279f0897119ecdcb8d41e382bcd9))
* improve error handling by downloading proto installer to temp file ([9016286](https://github.com/etalab-ia/rag-facile/commit/9016286f45514869f64a6435cb6a0b6e5e6572d4))
* move proxy env vars to installer step to avoid checkout failures ([ee33c05](https://github.com/etalab-ia/rag-facile/commit/ee33c059a29b3105676a123b016af06a851514cd))
* pass RAG_FACILE_BRANCH env var to installers in workflow ([5936cc5](https://github.com/etalab-ia/rag-facile/commit/5936cc514c1a3c2e9cd3cdb6b027d09a2603d486))
* pin Python 3.13.11 across all toolchain configurations ([19f68b6](https://github.com/etalab-ia/rag-facile/commit/19f68b6c0b8060b841e2bd415a6a116e0de0530b))
* preserve proxy environment variables when running proto installer ([f7271cc](https://github.com/etalab-ia/rag-facile/commit/f7271ccdd79e4177f294d24357d1154a77cce03b))
* prevent install.sh from exiting when no proxy is detected ([7418f99](https://github.com/etalab-ia/rag-facile/commit/7418f99159578a3f125e2f4dda5ecafabc78c00c))
* remove macOS Intel (macos-12) test - runners not available ([ba2a511](https://github.com/etalab-ia/rag-facile/commit/ba2a511c1f96a734053cf81d63afe5cbcbef2618))
* remove nested PowerShell call in Windows CI test ([b61a826](https://github.com/etalab-ia/rag-facile/commit/b61a82663cc13ff78eb06a0ef2412155f0ecac12))
* remove proxy simulation jobs from test-install workflow ([7eb2b9e](https://github.com/etalab-ia/rag-facile/commit/7eb2b9e1fdfaf2a7de4c9dcb55b6233c0baf1eea))
* replace process substitution with file download for installer ([051698d](https://github.com/etalab-ia/rag-facile/commit/051698d89932aad5a5b6bd89fc3ae9296caaa492))
* resolve issue [#46](https://github.com/etalab-ia/rag-facile/issues/46) - add proxy support for proto plugin installation ([c1aa693](https://github.com/etalab-ia/rag-facile/commit/c1aa693431af04f7278348be682981c12484b36b))
* simplify test-install workflow to only verify tool installation ([2d313f8](https://github.com/etalab-ia/rag-facile/commit/2d313f81df3d5ec0a5e646fefb724f75adb9bfba))
* source shell profile in workflow verification steps ([95761d5](https://github.com/etalab-ia/rag-facile/commit/95761d580855bfe0c29088604cd1ebb311687335))
* update install script to reference current setup command ([c06a947](https://github.com/etalab-ia/rag-facile/commit/c06a947c5593a0ea36db6c2a8aa85468211787cc))
* update install script to reference current setup command ([6ac8d99](https://github.com/etalab-ia/rag-facile/commit/6ac8d99464116745aabbec2c94515fc3d00edffa))
* use correct GitHub raw content URL format with refs/heads ([93087e0](https://github.com/etalab-ia/rag-facile/commit/93087e0756f5bb0964ec9c28a16f2b0787713c2d))
* use GITHUB_ENV to persist PATH across workflow steps ([64343cf](https://github.com/etalab-ia/rag-facile/commit/64343cf11a3da89c82b0555ffe0f9a75adb62476))
* use GITHUB_PATH for uv tools directory in CI ([86b4d35](https://github.com/etalab-ia/rag-facile/commit/86b4d357528de0eafcdd817742eaa6d66702d3c3))
* use github.head.ref for PR testing to avoid 404 errors ([5589820](https://github.com/etalab-ia/rag-facile/commit/558982041502d921e99859420aca837aee12ea47))
* use static directory names in reflex-chat template for Windows compatibility ([87a4f1f](https://github.com/etalab-ia/rag-facile/commit/87a4f1fc5bb6b50660f2f0b6e5b898b0b0063d64))
* use subexpression syntax for variable interpolation in PowerShell install script ([d0221e6](https://github.com/etalab-ia/rag-facile/commit/d0221e61e6365fd4ca05b92c7c2236e75b99cc55))


### Documentation

* docs:  ([3064ed2](https://github.com/etalab-ia/rag-facile/commit/3064ed21f0ea4d2c53fa045735e1279f4abfc8b9))
* add comprehensive Windows support documentation ([871e8fd](https://github.com/etalab-ia/rag-facile/commit/871e8fd6c61cf8294178868072307143573f508a))
* add Linux and macOS CI/CD testing guides with comprehensive workflow ([a2b9189](https://github.com/etalab-ia/rag-facile/commit/a2b9189019b51ffdfe268bac460fdea0717e002c))
* align documentation wording on just and moon commands ([d8f8a66](https://github.com/etalab-ia/rag-facile/commit/d8f8a66cb02c4901679e9c8558f316865ec5deb9))
* align documentation wording on just and moon commands ([581feb8](https://github.com/etalab-ia/rag-facile/commit/581feb89f58126148ac7b86ea8b044033e687dc2))
* reorganize documentation into dedicated docs directory ([1e43a1f](https://github.com/etalab-ia/rag-facile/commit/1e43a1f1d1b11f632c7e6dcf471b1397edaf6f99))
* update AGENTS.md with comprehensive current project knowledge ([cf15658](https://github.com/etalab-ia/rag-facile/commit/cf15658ff58ae592b3a119619cfa8b36c54c51b0))

## [0.6.1](https://github.com/etalab-ia/rag-facile/compare/v0.6.0...v0.6.1) (2026-02-05)


### Bug Fixes

* update remaining eval.providers references in test_document_preprocessor.py ([f0a423f](https://github.com/etalab-ia/rag-facile/commit/f0a423f1d1f5de28b07a0022a93edad649b8e29a))

## [0.6.0](https://github.com/etalab-ia/rag-facile/compare/v0.5.0...v0.6.0) (2026-02-04)


### Features

* add --debug flag and strengthen Albert sample count requirement ([a2a85d3](https://github.com/etalab-ia/rag-facile/commit/a2a85d30d292765e1522bfffc2cb1086b316ceb8))
* add Albert API provider for eval generate command ([467f8be](https://github.com/etalab-ia/rag-facile/commit/467f8be563b68cb3bd22f32f1ba75aa4b52407a7))
* add comprehensive logging for provider interactions and debugging ([a6d5f14](https://github.com/etalab-ia/rag-facile/commit/a6d5f146194cafd70eb151403c1642cbea8bfa2d))
* add debug output for provider IDs during eval generate ([52e48d7](https://github.com/etalab-ia/rag-facile/commit/52e48d7ae4a509a9332ed1c39430bad236443eaf))
* add document preprocessing with PDF extraction for eval providers ([e97504b](https://github.com/etalab-ia/rag-facile/commit/e97504b0af3a12a9dbfc6f71802738fb0b50583f))
* add new PDF sample files for testing and demonstration purposes. ([da9ea82](https://github.com/etalab-ia/rag-facile/commit/da9ea826e218492165082063461ae52b69bbb0e7))
* comprehensive eval generate improvements (PDF extraction, logging, debug flag) ([a6e431a](https://github.com/etalab-ia/rag-facile/commit/a6e431a75e7eeb722740c44442894a554c56a25c))
* **eval:** add Data Foundry synthetic Q/A generation ([6371225](https://github.com/etalab-ia/rag-facile/commit/63712250a8ea6883aff5caddeea0979e66b0e2cc))
* **eval:** add Data Foundry synthetic Q/A generation ([0fc3f4a](https://github.com/etalab-ia/rag-facile/commit/0fc3f4aa77a42e96c23e4f01a5f2927c3f924048))


### Bug Fixes

* **eval:** delete folder after generation to avoid storage limits ([2f53765](https://github.com/etalab-ia/rag-facile/commit/2f5376520cfbdce9ecfc258b7e424f07af0beb40))
* remove extra blank lines in cli README ([fc3eb90](https://github.com/etalab-ia/rag-facile/commit/fc3eb9079acfdc72ac7ee995168380d2db24f0d8))
* remove search and sources (list) commands from eval ([d171427](https://github.com/etalab-ia/rag-facile/commit/d1714277615370f7be1719427290d082e48cecb0))
* resolve ruff formatting issues ([b457b5c](https://github.com/etalab-ia/rag-facile/commit/b457b5ccde42421337f791aee76a31b6091cb494))
* strengthen Albert provider prompt to enforce JSONL-only output ([d735430](https://github.com/etalab-ia/rag-facile/commit/d735430f1740718449b2eeb50612e3bc4526baa5))
* strengthen Letta provider prompt to enforce JSONL-only output ([c6f1bba](https://github.com/etalab-ia/rag-facile/commit/c6f1bbae1474eb8b1829f95beb3fd791c4c392a3))


### Performance Improvements

* **eval:** use buffer for efficient streaming JSON parsing ([58fad11](https://github.com/etalab-ia/rag-facile/commit/58fad11adadf032c5a296923406b4086518807cb))


### Documentation

* add Albert API provider documentation ([b1f56d4](https://github.com/etalab-ia/rag-facile/commit/b1f56d45197ee81ff12111a65dad9f612afb1ea4))
* add eval generate command documentation ([027cb19](https://github.com/etalab-ia/rag-facile/commit/027cb19f5c445279ce996769648b474ec1a9c6c6))
* update documentation for eval generate improvements ([041b8fc](https://github.com/etalab-ia/rag-facile/commit/041b8fcfb31f00fd00144a3ec805c174887633b4))

## [0.5.0](https://github.com/etalab-ia/rag-facile/compare/v0.4.0...v0.5.0) (2026-02-03)


### Features

* add dataset filtering by task and language to search commands ([bc5c52d](https://github.com/etalab-ia/rag-facile/commit/bc5c52d48cc9bec6daa88a6dfacf17176319bfcb))
* add dataset filtering by task and language to search commands ([f3f95e2](https://github.com/etalab-ia/rag-facile/commit/f3f95e2f955d8cc3a75ac57e9f7d7b95e18ee4ce))


### Bug Fixes

* handle edge cases and follow PEP 8 in CLI ([b3cd4e3](https://github.com/etalab-ia/rag-facile/commit/b3cd4e3da31533a475744c08cd0853896fd573e7))
* remove duplicate 0.4.0 from CHANGELOG ([1f903dd](https://github.com/etalab-ia/rag-facile/commit/1f903dd17248e2a060ec1df01f0436498dfe14b4))
* show help when subcommands are missing ([bc3e862](https://github.com/etalab-ia/rag-facile/commit/bc3e862e7ed9419bd320c3363cfb52a1b3d23ac7))

## [0.4.0](https://github.com/etalab-ia/rag-facile/compare/v0.3.0...v0.4.0) (2026-02-03)


### Features

* add standalone project structure option for simpler setup ([962ebd2](https://github.com/etalab-ia/rag-facile/commit/962ebd235b593da28764bb84a58d79e311a05209))


### Bug Fixes

* ask project structure before frontend selection ([816c046](https://github.com/etalab-ia/rag-facile/commit/816c04662efb7f7f653505138791765a24d14ccf))
* make standalone test more robust for CI ([a0f89e3](https://github.com/etalab-ia/rag-facile/commit/a0f89e309afed26661eb45df28c8842dfaa3302b))


### Documentation

* add project structure comparison (Simple vs Monorepo) ([9a21910](https://github.com/etalab-ia/rag-facile/commit/9a219105a986d412e08606b73b7b19a41e809282))

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
