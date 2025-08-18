<a name="readme-top"></a>

<div align="center">
  <img src="./docs/static/images/icon.jpg" alt="Logo" width="200">
  <h1 align="center">Prometheus</h1>
</div>


<div align="center">
  <a href="https://github.com/Pantheon-temple/Prometheus/graphs/contributors"><img src="https://img.shields.io/github/contributors/Pantheon-temple/Prometheus?style=for-the-badge&color=blue" alt="Contributors"></a>
  <a href="https://github.com/Pantheon-temple/Prometheus/stargazers"><img src="https://img.shields.io/github/stars/Pantheon-temple/Prometheus?style=for-the-badge&color=blue" alt="Stargazers"></a>
  <a href="https://github.com/Pantheon-temple/Prometheus/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Pantheon-temple/Prometheus?style=for-the-badge&color=blue" alt="APACHE-2.0 License"></a>
  <a href="https://www.arxiv.org/abs/2507.19942"><img src="https://img.shields.io/badge/Paper-arXiv-red?style=for-the-badge&logo=arxiv" alt="Paper"></a>
  <br/>
    <a href="https://github.com/Pantheon-temple/Prometheus/blob/main/CREDITS.md"><img src="https://img.shields.io/badge/Project-Credits-blue?style=for-the-badge&color=FFE165&logo=github&logoColor=white" alt="Credits"></a>
  <br/>
  <hr>
</div>


![Code Coverage](https://github.com/Pantheon-temple/Prometheus/raw/coverage-badge/coverage.svg)

# Prometheus

Prometheus is a FastAPI-based backend service designed to perform intelligent codebase-level operations, including
answering questions, resolving issues, and reviewing pull requests. At its core, it implements a multi-agent approach
governed by a state machine to ensure code quality through automated reviews, build verification, and test execution.

## 🚀 Features

- **Codebase Analysis**: Answer questions about your codebase and provide insights.
- **Issue Resolution**: Automatically resolve issues in your repository.
- **Pull Request Reviews**: Perform intelligent reviews of pull requests to ensure code quality.
- **Multi-Agent System**: Uses a state machine to coordinate multiple agents for efficient task execution.
- **Integration with External Services**: Seamlessly connects with other services in the `Pantheon-temple` organization.

## 📊 Evaluation Results on SWE-bench Lite

<div align="center">
  <img src="./docs/static/images/comparison_deepseek_July08.png" alt="SWE-bench Lite Result" width="800"/>
  <p><em>Success Rate Comparison across popular agents. Prometheus achieves 28.67%.</em></p>
</div>


```bibtex
@misc{Prometheus-code-agent-2025,
      title={Prometheus: Unified Knowledge Graphs for Issue Resolution in Multilingual Codebases}, 
      author={Zimin Chen and Yue Pan and Siyu Lu and Jiayi Xu and Claire Le Goues and Martin Monperrus and He Ye},
      year={2025},
      eprint={2507.19942},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2507.19942}, 
}
```

## ⚙️ Quick Start

### ✅ Prerequisites

- Docker
- Docker Compose
- API keys (e.g. OpenAI, Anthropic, Google Gemini)

---

### 📦 Setup

1. #### Clone the repository:
   ```bash
   git clone https://github.com/Pantheon-temple/Prometheus.git
   cd Prometheus
   ```

2. #### Copy the `example.env` file to `.env` and update it with your API keys and other required configurations:

   ```bash
   mv example.env .env
   ```

   > You need to provide a secure `JWT_SECRET_KEY` in the `.env` file.
   > You can generate a strong key by running the following command:

   ```bash
   python -m prometheus.script.generate_jwt_token
   ```

   This will print a secure token you can copy and paste into your `.env` file

3. #### Create the working directory to store logs and cloned repositories:

   ```bash
   mkdir working_dir
   ```

4. #### Start the services using Docker Compose:

    - **Linux (includes PostgreSQL)**:
      ```bash
      docker-compose up --build
      ```

    - **macOS / Windows**:

      > ⚠️ `docker-compose.win_mac.yml` does **not include PostgreSQL**.If you don't have PostgreSQL on your device,
      you may have to start the PostgreSQL container manually **before starting services** by following the "Database
      Setup" section below.

      ```bash
      docker-compose -f docker-compose.win_mac.yml up --build
      ```

5. #### Access Prometheus:
    - Service: [http://localhost:9002/v1.2](http://localhost:9002/v1.2)
    - OpenAPI Docs: [http://localhost:9002/docs](http://localhost:9002/docs)

6. #### Upload Your Codebase:

   You can upload a GitHub repository to Prometheus using the following API endpoint:

   - **Endpoint:** `POST /repository/upload/`
     - **Request Body:** JSON object matching the `UploadRepositoryRequest` schema (see [API Documents](http://127.0.0.1:9002/docs#/repository/repository-upload_github_repository))

   This will clone the specified repository (defaulting to the latest commit on the main branch) into Prometheus.

7. #### 📝 Answer Repository Issues

   You can ask Prometheus to analyze and answer a specific issue in your codebase using the `/issue/answer/` API endpoint.
   
   - **Endpoint:** `POST /issue/answer/`
     - **Request Body:** JSON object matching the `IssueRequest` schema (see [API Documents](http://127.0.0.1:9002/docs#/issue/issue-answer_issue))
     - **Response:** Returns the generated patch, test/build results, and a summary response.

---

## 🗄️ Database Setup

### PostgreSQL

> ⚠️ If you're using `docker-compose.win_mac.yml`, you may have to manually start PostgreSQL before launching
> Prometheus:

Run the following command to start a PostgreSQL container:

```bash
docker run -d \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=postgres \
  postgres
```

### Neo4j

Run the following command to start a Neo4j container:

```bash
docker run -d \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS='["apoc"]' \
  -e NEO4J_dbms_memory_heap_initial__size=4G \
  -e NEO4J_dbms_memory_heap_max__size=8G \
  -e NEO4J_dbms_memory_pagecache_size=4G \
  neo4j
```

Verify Neo4J at: [http://localhost:7474](http://localhost:7474)

---

## 🧪 Development

### Requirements

* Python 3.11+

### Steps

1. Install dependencies:

   ```bash
   pip install hatchling
   pip install .
   pip install .[test]
   ```

2. Run tests:

   ```bash
   coverage run --source=prometheus -m pytest -v -s -m "not git"
   ```

3. Generate coverage report:

   ```bash
   coverage report -m
   ```
4. Generate HTML report:

   ```bash
   coverage html
   open htmlcov/index.html
   ```

5. Start dev server:

   ```bash
   uvicorn prometheus.app.main:app --host 0.0.0.0 --port 9002
   ```

---

## 📄 License

Licensed under the [Apache License 2.0](LICENSE).

---

## 📬 Contact

For questions or support, please open an issue in
the [GitHub repository](https://github.com/Pantheon-temple/Prometheus/issues).
