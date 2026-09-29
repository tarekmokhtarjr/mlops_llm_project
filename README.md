# Configuration Explanation

This document explains each configuration parameter used in the `.env` file and `docker-compose-dev.yml` file.

## .env File Configurations

| Parameter                  | Description                                                                                      | Example Value                           |
|----------------------------|--------------------------------------------------------------------------------------------------|-----------------------------------------|
| CHATBOT_MODEL              | Specifies the model to be used for the chatbot.                                                  | `Qwen/Qwen2.5-0.5B-Instruct`             |
| CHATBOT_SERVER             | URL of the chatbot server.                                                                       | `http://localhost`                      |
| CHATBOT_SERVER_PORT        | Port of the chatbot server.                                                                       | `8000`                                  |
| CHATBOT_API_KEY            | API key for the chatbot server.                                                                   | `dumb`                                |
| EMBEDDING_MODEL            | Specifies the model to be used for embeddings.                                                       | `Qwen/Qwen3-Embedding-0.6B`            |
| EMBEDDING_MODEL_SERVER     | URL of the embedding model server.                                                               | `http://localhost`                      |
| EMBEDDING_MODEL_SERVER_PORT| Port of the embedding model server.                                                               | `8001`                                  |
| EMBEDDING_MODEL_API_KEY    | API key for the embedding model server.                                                           | `dumb`                                |
| GUARD_IMAGE                | Docker image for the LLM Guard.                                                                  | `vllm/vllm-openai-cpu:v0.29.0`         |
| GUARD_CONTAINER_NAME       | Name of the LLM Guard container.                                                                 | `qwen3-guard`                         |
| GUARD_RESTART_POLICY       | Restart policy for the LLM Guard container.                                                        | `unless-stopped`                      |
| GUARD_PORT_HOST            | Host port for the LLM Guard.                                                                     | `8002`                                |
| GUARD_PORT_CONTAINER       | Container port for the LLM Guard.                                                                | `8000`                                |
| GUARD_VOLUME               | Volume for the LLM Guard.                                                                        | `hf_cache`                            |
| GUARD_VLLM_CPU_KVCACHE_SPACE | CPU KVCache space for VLLM.                                                                 | `1`                                   |
| GUARD_VLLM_ENABLE_V1_MULTIPROCESSING | Enable V1 multiprocessing for VLLM.                                                       | `0`                                   |
| GUARD_VLLM_LOGGING_LEVEL   | Logging level for VLLM.                                                                          | `INFO`                                |
| GUARD_CPUSET               | CPU set for the LLM Guard.                                                                       | `0-7`                                 |
| GUARD_COMMAND              | Command to run the LLM Guard.                                                                    | `Qwen/Qwen3Guard-Gen-0.6B`             |
| GUARD_MODEL                | Name of the served model for the LLM Guard.                                                       | `Qwen/Qwen3Guard-Gen-0.6B`             |
| GUARD_HOST                 | Host for the LLM Guard.                                                                          | `0.0.0.0`                             |
| GUARD_PORT                 | Port for the LLM Guard.                                                                          | `8000`                                |
| GUARD_MAX_MODEL_LEN        | Maximum model length for the LLM Guard.                                                           | `2048`                                |
| GUARD_SECURITY_OPT         | Security option for the LLM Guard.                                                               | `seccomp=unconfined`                    |
| GUARD_CAP_ADD              | Capability to add for the LLM Guard.                                                             | `SYS_NICE`                            |
| GUARD_NETWORK              | Network for the LLM Guard.                                                                       | `rag-net`                             |