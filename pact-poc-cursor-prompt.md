# Pact.io POC — Cursor Prompt

## Задача

Создай полноценный **Pact Contract Testing POC** в одном репозитории.
Всё должно запускаться одной командой: `docker-compose up --build`

---

## Структура проекта

```
pact-poc/
├── docker-compose.yml
├── consumer/                  # order-service (Python/Flask)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   └── tests/
│       ├── conftest.py
│       ├── test_user_pact.py
│       └── test_product_pact.py
├── provider-user/             # user-service (Python/Flask)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
├── provider-product/          # product-service (Python/Flask)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
├── pact-dashboard/            # React визуализация (Vite + React)
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       │   └── brokerApi.js
│       └── components/
│           ├── DependencyGraph.jsx
│           ├── CompatibilityMatrix.jsx
│           ├── ContractList.jsx
│           └── VerificationTimeline.jsx
├── jenkins/
│   ├── Dockerfile
│   └── pipelines/
│       ├── Jenkinsfile.consumer
│       ├── Jenkinsfile.provider-user
│       └── Jenkinsfile.provider-product
└── scripts/
    ├── publish-pacts.sh
    ├── verify-provider-user.sh
    ├── verify-provider-product.sh
    └── can-i-deploy.sh
```

---

## Сервисы и порты

| Контейнер         | Описание                      | Порт  |
|-------------------|-------------------------------|-------|
| `postgres`        | БД для Pact Broker            | 5432  |
| `pact-broker`     | Pact Broker UI + API          | 9292  |
| `consumer`        | order-service Flask           | 5000  |
| `provider-user`   | user-service Flask            | 5001  |
| `provider-product`| product-service Flask         | 5002  |
| `jenkins`         | Jenkins CI/CD                 | 8080  |
| `pact-dashboard`  | React Dashboard (nginx)       | 3000  |

---

## docker-compose.yml

Создай `docker-compose.yml` со следующими сервисами:

```yaml
version: "3.8"

services:

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: pact
      POSTGRES_PASSWORD: pact
      POSTGRES_DB: pact_broker
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pact"]
      interval: 5s
      timeout: 5s
      retries: 10

  pact-broker:
    image: pactfoundation/pact-broker:latest
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "9292:9292"
    environment:
      PACT_BROKER_DATABASE_URL: "postgres://pact:pact@postgres/pact_broker"
      PACT_BROKER_BASIC_AUTH_USERNAME: admin
      PACT_BROKER_BASIC_AUTH_PASSWORD: admin
      PACT_BROKER_ALLOW_PUBLIC_READ: "true"
      PACT_BROKER_PUBLIC_BROKER_HOST: localhost
      PACT_BROKER_PORT: 9292
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9292/diagnostic/status/heartbeat"]
      interval: 10s
      timeout: 5s
      retries: 10

  provider-user:
    build: ./provider-user
    ports:
      - "5001:5001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 5s
      retries: 5

  provider-product:
    build: ./provider-product
    ports:
      - "5002:5002"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5002/health"]
      interval: 5s
      retries: 5

  consumer:
    build: ./consumer
    ports:
      - "5000:5000"
    depends_on:
      provider-user:
        condition: service_healthy
      provider-product:
        condition: service_healthy
      pact-broker:
        condition: service_healthy
    environment:
      USER_SERVICE_URL: http://provider-user:5001
      PRODUCT_SERVICE_URL: http://provider-product:5002
      PACT_BROKER_URL: http://pact-broker:9292
      PACT_BROKER_USERNAME: admin
      PACT_BROKER_PASSWORD: admin

  jenkins:
    build: ./jenkins
    ports:
      - "8080:8080"
      - "50000:50000"
    depends_on:
      pact-broker:
        condition: service_healthy
    volumes:
      - jenkins_data:/var/jenkins_home
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      JAVA_OPTS: "-Djenkins.install.runSetupWizard=false"

  pact-dashboard:
    build: ./pact-dashboard
    ports:
      - "3000:80"
    depends_on:
      pact-broker:
        condition: service_healthy

volumes:
  postgres_data:
  jenkins_data:
```

---

## Consumer — order-service (Python/Flask)

### `consumer/requirements.txt`
```
flask==3.0.0
requests==2.31.0
pact-python==2.2.1
pytest==7.4.3
pytest-pact==0.1.4
```

### `consumer/app.py`

Flask приложение `order-service`. Оно вызывает два провайдера:

```python
import os, requests
from flask import Flask, jsonify

app = Flask(__name__)

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:5001")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:5002")

@app.route("/order/<int:user_id>/<int:product_id>")
def create_order(user_id, product_id):
    user = requests.get(f"{USER_SERVICE_URL}/users/{user_id}").json()
    product = requests.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}").json()
    return jsonify({
        "order_id": 1,
        "user": user,
        "product": product,
        "total": product["price"]
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### `consumer/tests/conftest.py`

```python
import pytest
from pact import Consumer, Provider

PACT_DIR = "pacts"
PACT_MOCK_HOST = "localhost"

@pytest.fixture(scope="session")
def pact_user():
    pact = Consumer("order-service").has_pact_with(
        Provider("user-service"),
        host_name=PACT_MOCK_HOST,
        port=1234,
        pact_dir=PACT_DIR,
        log_dir="logs"
    )
    pact.start_service()
    yield pact
    pact.stop_service()

@pytest.fixture(scope="session")
def pact_product():
    pact = Consumer("order-service").has_pact_with(
        Provider("product-service"),
        host_name=PACT_MOCK_HOST,
        port=1235,
        pact_dir=PACT_DIR,
        log_dir="logs"
    )
    pact.start_service()
    yield pact
    pact.stop_service()
```

### `consumer/tests/test_user_pact.py`

```python
import requests
from pact import Like, Term

def test_get_user(pact_user):
    expected = {"id": 1, "name": Like("John Doe"), "email": Term(r".+@.+\..+", "john@example.com")}

    (pact_user
        .given("user 1 exists")
        .upon_receiving("a request for user 1")
        .with_request("GET", "/users/1")
        .will_respond_with(200, body=expected))

    with pact_user:
        result = requests.get("http://localhost:1234/users/1")
        assert result.status_code == 200
        data = result.json()
        assert "id" in data
        assert "name" in data
        assert "email" in data
```

### `consumer/tests/test_product_pact.py`

```python
import requests
from pact import Like

def test_get_product(pact_product):
    expected = {"id": 1, "name": Like("Widget"), "price": Like(9.99)}

    (pact_product
        .given("product 1 exists")
        .upon_receiving("a request for product 1")
        .with_request("GET", "/products/1")
        .will_respond_with(200, body=expected))

    with pact_product:
        result = requests.get("http://localhost:1235/products/1")
        assert result.status_code == 200
        data = result.json()
        assert "id" in data
        assert "name" in data
        assert "price" in data

def test_create_product(pact_product):
    request_body = {"name": Like("Gadget"), "price": Like(19.99)}
    expected = {"id": Like(2), "name": Like("Gadget"), "price": Like(19.99)}

    (pact_product
        .given("a product can be created")
        .upon_receiving("a request to create a product")
        .with_request("POST", "/products", body=request_body, headers={"Content-Type": "application/json"})
        .will_respond_with(201, body=expected))

    with pact_product:
        result = requests.post(
            "http://localhost:1235/products",
            json={"name": "Gadget", "price": 19.99}
        )
        assert result.status_code == 201
```

### `consumer/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl ruby ruby-dev && gem install pact-mock_service
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

---

## Provider User — user-service (Python/Flask)

### `provider-user/app.py`

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

USERS = {
    1: {"id": 1, "name": "John Doe", "email": "john@example.com"},
    2: {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
}

@app.route("/users/<int:user_id>")
def get_user(user_id):
    user = USERS.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# Pact provider state endpoint — используется при верификации
@app.route("/pact-setup", methods=["POST"])
def pact_setup():
    state = request.json.get("state", "")
    if state == "user 1 exists":
        USERS[1] = {"id": 1, "name": "John Doe", "email": "john@example.com"}
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
```

### `provider-user/requirements.txt`
```
flask==3.0.0
pact-python==2.2.1
requests==2.31.0
```

---

## Provider Product — product-service (Python/Flask)

### `provider-product/app.py`

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

PRODUCTS = {
    1: {"id": 1, "name": "Widget", "price": 9.99},
    2: {"id": 2, "name": "Gadget", "price": 19.99},
}
_next_id = 3

@app.route("/products/<int:product_id>")
def get_product(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product)

@app.route("/products", methods=["POST"])
def create_product():
    global _next_id
    data = request.json
    product = {"id": _next_id, "name": data["name"], "price": data["price"]}
    PRODUCTS[_next_id] = product
    _next_id += 1
    return jsonify(product), 201

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# Pact provider state endpoint
@app.route("/pact-setup", methods=["POST"])
def pact_setup():
    state = request.json.get("state", "")
    if state == "product 1 exists":
        PRODUCTS[1] = {"id": 1, "name": "Widget", "price": 9.99}
    if state == "a product can be created":
        pass  # no setup needed
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
```

### `provider-product/requirements.txt`
```
flask==3.0.0
pact-python==2.2.1
requests==2.31.0
```

---

## Jenkins

### `jenkins/Dockerfile`

```dockerfile
FROM jenkins/jenkins:lts-jdk17

USER root

RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    ruby ruby-dev \
    curl docker.io \
    && gem install pact-mock_service pact_broker-client \
    && rm -rf /var/lib/apt/lists/*

# Отключаем мастер-ключ для автоматического запуска
COPY jenkins-config/plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

COPY jenkins-config/jenkins.yaml /var/jenkins_home/casc_configs/jenkins.yaml

ENV CASC_JENKINS_CONFIG=/var/jenkins_home/casc_configs/jenkins.yaml
ENV JENKINS_OPTS="--httpPort=8080"

USER jenkins
```

### `jenkins/jenkins-config/plugins.txt`

```
configuration-as-code
workflow-aggregator
git
pipeline-stage-view
docker-workflow
credentials-binding
ansicolor
```

### `jenkins/jenkins-config/jenkins.yaml`

JCasC конфиг — создаёт jobs автоматически при старте Jenkins:

```yaml
jenkins:
  securityRealm:
    local:
      allowsSignup: false
      users:
        - id: "admin"
          password: "admin"
  authorizationStrategy:
    loggedInUsersCanDoAnything:
      allowAnonymousRead: true
  numExecutors: 4

jobs:
  - script: |
      pipelineJob('01-consumer-pact-tests') {
        definition {
          cpsScm {
            scm {
              gitSCM {
                userRemoteConfigs {
                  userRemoteConfig {
                    url('http://host.docker.internal/pact-poc')
                  }
                }
                branches { branchSpec { name('*/main') } }
              }
            }
            scriptPath('jenkins/pipelines/Jenkinsfile.consumer')
          }
        }
      }
  - script: |
      pipelineJob('02-provider-user-verify') {
        definition {
          cpsScm {
            scm {
              gitSCM {
                userRemoteConfigs {
                  userRemoteConfig {
                    url('http://host.docker.internal/pact-poc')
                  }
                }
                branches { branchSpec { name('*/main') } }
              }
            }
            scriptPath('jenkins/pipelines/Jenkinsfile.provider-user')
          }
        }
      }
  - script: |
      pipelineJob('03-provider-product-verify') {
        definition {
          cpsScm {
            scm {
              gitSCM {
                userRemoteConfigs {
                  userRemoteConfig {
                    url('http://host.docker.internal/pact-poc')
                  }
                }
                branches { branchSpec { name('*/main') } }
              }
            }
            scriptPath('jenkins/pipelines/Jenkinsfile.provider-product')
          }
        }
      }
```

### `jenkins/pipelines/Jenkinsfile.consumer`

```groovy
pipeline {
    agent any
    environment {
        PACT_BROKER_URL    = 'http://pact-broker:9292'
        PACT_BROKER_USER   = 'admin'
        PACT_BROKER_PASS   = 'admin'
        CONSUMER_VERSION   = "${env.BUILD_NUMBER ?: '1.0.0'}"
    }
    stages {
        stage('Install deps') {
            steps {
                dir('consumer') {
                    sh 'python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt'
                }
            }
        }
        stage('Run Pact consumer tests') {
            steps {
                dir('consumer') {
                    sh '. venv/bin/activate && pytest tests/ -v'
                }
            }
        }
        stage('Publish pacts to Broker') {
            steps {
                dir('consumer') {
                    sh """
                        pact-broker publish pacts/ \
                          --broker-base-url=${PACT_BROKER_URL} \
                          --broker-username=${PACT_BROKER_USER} \
                          --broker-password=${PACT_BROKER_PASS} \
                          --consumer-app-version=${CONSUMER_VERSION} \
                          --tag main
                    """
                }
            }
        }
        stage('Can I Deploy?') {
            steps {
                sh """
                    pact-broker can-i-deploy \
                      --broker-base-url=${PACT_BROKER_URL} \
                      --broker-username=${PACT_BROKER_USER} \
                      --broker-password=${PACT_BROKER_PASS} \
                      --pacticipant order-service \
                      --version ${CONSUMER_VERSION} \
                      --to-environment production \
                      --retry-while-unknown 10 \
                      --retry-interval 5 \
                      --ignore-no-pacts-for-provider || true
                """
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'consumer/pacts/*.json', allowEmptyArchive: true
        }
    }
}
```

### `jenkins/pipelines/Jenkinsfile.provider-user`

```groovy
pipeline {
    agent any
    environment {
        PACT_BROKER_URL   = 'http://pact-broker:9292'
        PACT_BROKER_USER  = 'admin'
        PACT_BROKER_PASS  = 'admin'
        PROVIDER_VERSION  = "${env.BUILD_NUMBER ?: '1.0.0'}"
        PROVIDER_BASE_URL = 'http://provider-user:5001'
    }
    stages {
        stage('Install deps') {
            steps {
                dir('provider-user') {
                    sh 'python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt'
                }
            }
        }
        stage('Verify pacts from Broker') {
            steps {
                dir('provider-user') {
                    sh """
                        . venv/bin/activate
                        pact-verifier \
                          --provider-base-url=${PROVIDER_BASE_URL} \
                          --provider-states-setup-url=${PROVIDER_BASE_URL}/pact-setup \
                          --pact-broker-base-url=${PACT_BROKER_URL} \
                          --broker-username=${PACT_BROKER_USER} \
                          --broker-password=${PACT_BROKER_PASS} \
                          --provider=user-service \
                          --provider-app-version=${PROVIDER_VERSION} \
                          --tag-with-git-branch \
                          --publish-verification-results
                    """
                }
            }
        }
        stage('Can I Deploy?') {
            steps {
                sh """
                    pact-broker can-i-deploy \
                      --broker-base-url=${PACT_BROKER_URL} \
                      --broker-username=${PACT_BROKER_USER} \
                      --broker-password=${PACT_BROKER_PASS} \
                      --pacticipant user-service \
                      --version ${PROVIDER_VERSION} \
                      --to-environment production \
                      --retry-while-unknown 10 \
                      --retry-interval 5 || true
                """
            }
        }
    }
}
```

### `jenkins/pipelines/Jenkinsfile.provider-product`

Аналогично `Jenkinsfile.provider-user`, но:
- `PROVIDER_BASE_URL = 'http://provider-product:5002'`
- `--provider=product-service`
- `dir('provider-product')`

---

## React Dashboard — pact-dashboard

### `pact-dashboard/Dockerfile`

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### `pact-dashboard/nginx.conf`

```nginx
server {
    listen 80;

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # Проксируем API запросы к Pact Broker
    location /api/broker/ {
        proxy_pass http://pact-broker:9292/;
        proxy_set_header Authorization "Basic YWRtaW46YWRtaW4=";
        proxy_set_header Accept "application/hal+json";
        add_header Access-Control-Allow-Origin *;
    }
}
```

### `pact-dashboard/package.json`

```json
{
  "name": "pact-dashboard",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-flow-renderer": "^10.3.17",
    "recharts": "^2.10.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0"
  }
}
```

### `pact-dashboard/src/api/brokerApi.js`

```javascript
import axios from 'axios';

const BASE = '/api/broker';

export const fetchPacticipants = () =>
  axios.get(`${BASE}/pacticipants`).then(r => r.data._embedded?.pacticipants || []);

export const fetchMatrix = () =>
  axios.get(`${BASE}/matrix?q[][pacticipant]=order-service&latestby=cvpv`).then(r => r.data);

export const fetchIntegrations = () =>
  axios.get(`${BASE}/integrations`).then(r => r.data._embedded?.integrations || []);

export const fetchPacts = () =>
  axios.get(`${BASE}/pacts`).then(r => r.data._embedded?.pacts || []);
```

### `pact-dashboard/src/App.jsx`

```jsx
import { useState, useEffect } from 'react';
import DependencyGraph from './components/DependencyGraph';
import CompatibilityMatrix from './components/CompatibilityMatrix';
import ContractList from './components/ContractList';
import { fetchPacticipants, fetchMatrix, fetchIntegrations, fetchPacts } from './api/brokerApi';

export default function App() {
  const [tab, setTab] = useState('graph');
  const [pacticipants, setPacticipants] = useState([]);
  const [matrix, setMatrix] = useState(null);
  const [integrations, setIntegrations] = useState([]);
  const [pacts, setPacts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchPacticipants().then(setPacticipants),
      fetchMatrix().then(setMatrix),
      fetchIntegrations().then(setIntegrations),
      fetchPacts().then(setPacts),
    ]).finally(() => setLoading(false));
  }, []);

  const tabs = [
    { id: 'graph', label: '🔗 Dependency Graph' },
    { id: 'matrix', label: '✅ Compatibility Matrix' },
    { id: 'contracts', label: '📄 Contracts' },
  ];

  return (
    <div style={{ fontFamily: 'Inter, sans-serif', minHeight: '100vh', background: '#0f172a', color: '#e2e8f0' }}>
      <header style={{ background: '#1e293b', padding: '16px 32px', borderBottom: '1px solid #334155', display: 'flex', alignItems: 'center', gap: 16 }}>
        <span style={{ fontSize: 24 }}>⚡</span>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, color: '#f1f5f9' }}>Pact Dashboard</h1>
        <nav style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: tab === t.id ? '#6366f1' : '#334155',
              color: tab === t.id ? '#fff' : '#94a3b8', fontWeight: 500, fontSize: 14
            }}>{t.label}</button>
          ))}
        </nav>
      </header>

      <main style={{ padding: 32 }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 80, color: '#64748b' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⏳</div>
            <div>Loading from Pact Broker...</div>
          </div>
        ) : (
          <>
            {tab === 'graph' && <DependencyGraph integrations={integrations} pacticipants={pacticipants} />}
            {tab === 'matrix' && <CompatibilityMatrix matrix={matrix} />}
            {tab === 'contracts' && <ContractList pacts={pacts} />}
          </>
        )}
      </main>
    </div>
  );
}
```

### `pact-dashboard/src/components/DependencyGraph.jsx`

Компонент визуализирует граф зависимостей сервисов.
Используй `react-flow-renderer` для отрисовки узлов и рёбер.

```jsx
import ReactFlow, { Background, Controls, MiniMap } from 'react-flow-renderer';

export default function DependencyGraph({ integrations, pacticipants }) {
  // Строим nodes из pacticipants
  const nodes = pacticipants.map((p, i) => ({
    id: p.name,
    data: { label: p.name },
    position: { x: (i % 3) * 250 + 100, y: Math.floor(i / 3) * 150 + 80 },
    style: {
      background: '#1e293b', border: '2px solid #6366f1',
      color: '#e2e8f0', borderRadius: 12, padding: '12px 20px', fontWeight: 600
    }
  }));

  // Строим edges из integrations
  const edges = integrations.map((intg, i) => ({
    id: `e-${i}`,
    source: intg._embedded?.consumer?.name,
    target: intg._embedded?.provider?.name,
    animated: true,
    style: { stroke: '#6366f1' },
    label: 'consumes',
    labelStyle: { fill: '#94a3b8', fontSize: 11 }
  })).filter(e => e.source && e.target);

  return (
    <div style={{ background: '#1e293b', borderRadius: 16, border: '1px solid #334155', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px', borderBottom: '1px solid #334155' }}>
        <h2 style={{ margin: 0, fontSize: 18, color: '#f1f5f9' }}>Service Dependency Graph</h2>
        <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: 14 }}>
          {pacticipants.length} services · {integrations.length} integrations
        </p>
      </div>
      <div style={{ height: 500 }}>
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <Background color="#334155" gap={20} />
          <Controls />
          <MiniMap nodeColor="#6366f1" maskColor="rgba(0,0,0,0.5)" />
        </ReactFlow>
      </div>
    </div>
  );
}
```

### `pact-dashboard/src/components/CompatibilityMatrix.jsx`

Отображает матрицу совместимости версий consumer/provider.
Зелёный = верификация прошла, красный = провалилась, серый = нет данных.

```jsx
export default function CompatibilityMatrix({ matrix }) {
  if (!matrix) return <div style={{ color: '#64748b' }}>No matrix data</div>;

  const rows = matrix.matrix || [];

  return (
    <div style={{ background: '#1e293b', borderRadius: 16, border: '1px solid #334155', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px', borderBottom: '1px solid #334155' }}>
        <h2 style={{ margin: 0, fontSize: 18, color: '#f1f5f9' }}>Compatibility Matrix</h2>
        <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: 14 }}>Consumer vs Provider version compatibility</p>
      </div>
      <div style={{ overflowX: 'auto', padding: 24 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #334155' }}>
              {['Consumer', 'Version', 'Provider', 'Version', 'Status', 'Date'].map(h => (
                <th key={h} style={{ padding: '10px 16px', textAlign: 'left', color: '#64748b', fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const success = row.verificationResult?.success;
              return (
                <tr key={i} style={{ borderBottom: '1px solid #1e293b', background: i % 2 ? '#0f172a' : 'transparent' }}>
                  <td style={{ padding: '12px 16px', color: '#a5b4fc', fontWeight: 600 }}>{row.consumer?.name}</td>
                  <td style={{ padding: '12px 16px', color: '#94a3b8', fontFamily: 'monospace' }}>{row.consumer?.version?.number}</td>
                  <td style={{ padding: '12px 16px', color: '#34d399', fontWeight: 600 }}>{row.provider?.name}</td>
                  <td style={{ padding: '12px 16px', color: '#94a3b8', fontFamily: 'monospace' }}>{row.provider?.version?.number}</td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{
                      padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
                      background: success === true ? '#14532d' : success === false ? '#7f1d1d' : '#1e293b',
                      color: success === true ? '#4ade80' : success === false ? '#f87171' : '#64748b'
                    }}>
                      {success === true ? '✓ verified' : success === false ? '✗ failed' : '? unknown'}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', color: '#475569', fontSize: 12 }}>
                    {row.verificationResult?.verifiedAt ? new Date(row.verificationResult.verifiedAt).toLocaleDateString() : '—'}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr><td colSpan={6} style={{ padding: 40, textAlign: 'center', color: '#475569' }}>
                No verification data yet. Run CI pipelines to populate.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

### `pact-dashboard/src/components/ContractList.jsx`

```jsx
export default function ContractList({ pacts }) {
  return (
    <div style={{ background: '#1e293b', borderRadius: 16, border: '1px solid #334155', overflow: 'hidden' }}>
      <div style={{ padding: '20px 24px', borderBottom: '1px solid #334155' }}>
        <h2 style={{ margin: 0, fontSize: 18, color: '#f1f5f9' }}>Active Contracts</h2>
        <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: 14 }}>{pacts.length} contracts published</p>
      </div>
      <div style={{ padding: 24, display: 'grid', gap: 16 }}>
        {pacts.map((pact, i) => (
          <div key={i} style={{ background: '#0f172a', borderRadius: 12, padding: 20, border: '1px solid #334155' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
              <span style={{ fontSize: 20 }}>📄</span>
              <div>
                <div style={{ fontWeight: 600, color: '#f1f5f9' }}>
                  {pact._embedded?.consumer?.name} → {pact._embedded?.provider?.name}
                </div>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                  Created: {pact.createdAt ? new Date(pact.createdAt).toLocaleString() : '—'}
                </div>
              </div>
              <a href={`http://localhost:9292${pact._links?.self?.href}`} target="_blank" rel="noreferrer"
                style={{ marginLeft: 'auto', color: '#6366f1', fontSize: 12, textDecoration: 'none' }}>
                View in Broker →
              </a>
            </div>
          </div>
        ))}
        {pacts.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: '#475569' }}>
            No contracts published yet. Run consumer tests first.
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## Scripts — запуск всего вручную (без Jenkins)

### `scripts/publish-pacts.sh`
```bash
#!/bin/bash
set -e
echo "=== Running consumer pact tests ==="
cd consumer
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -q
pytest tests/ -v

echo "=== Publishing pacts to broker ==="
pact-broker publish pacts/ \
  --broker-base-url=http://localhost:9292 \
  --broker-username=admin \
  --broker-password=admin \
  --consumer-app-version=1.0.0 \
  --tag main

echo "✅ Pacts published!"
```

### `scripts/verify-provider-user.sh`
```bash
#!/bin/bash
set -e
echo "=== Verifying user-service ==="
pact-verifier \
  --provider-base-url=http://localhost:5001 \
  --provider-states-setup-url=http://localhost:5001/pact-setup \
  --pact-broker-base-url=http://localhost:9292 \
  --broker-username=admin \
  --broker-password=admin \
  --provider=user-service \
  --provider-app-version=1.0.0 \
  --publish-verification-results
echo "✅ user-service verified!"
```

### `scripts/can-i-deploy.sh`
```bash
#!/bin/bash
set -e
SERVICE=${1:-"order-service"}
VERSION=${2:-"1.0.0"}

echo "=== Can I deploy $SERVICE v$VERSION? ==="
pact-broker can-i-deploy \
  --broker-base-url=http://localhost:9292 \
  --broker-username=admin \
  --broker-password=admin \
  --pacticipant "$SERVICE" \
  --version "$VERSION" \
  --to-environment production
```

---

## BROKEN CONTRACT DEMO — обязательно включи это

Создай файл `provider-product/app_broken.py` — это версия product-service с намеренно сломанным контрактом:

```python
# BROKEN VERSION — поле 'price' переименовано в 'cost'
# Это сломает верификацию Pact контракта!
@app.route("/products/<int:product_id>")
def get_product(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    # BUG: consumer ожидает 'price', мы возвращаем 'cost'
    return jsonify({
        "id": product["id"],
        "name": product["name"],
        "cost": product["price"]   # <-- BREAKING CHANGE
    })
```

Добавь в `README.md` инструкцию "Демо сломанного контракта":
```
## Demo: Breaking Contract

1. Замени app.py в provider-product на содержимое app_broken.py
2. Перезапусти контейнер: docker-compose restart provider-product
3. Запусти Jenkins job "03-provider-product-verify"
4. Наблюдай как верификация падает с ошибкой:
   "expected 'price' but got 'cost'"
5. Pact Broker UI покажет красный статус в матрице
6. can-i-deploy вернёт "NO" — деплой заблокирован
```

---

## README.md

Создай подробный `README.md` со следующими разделами:

```markdown
# Pact Contract Testing POC

## Быстрый старт
docker-compose up --build

## Сервисы
| Сервис          | URL                    |
|-----------------|------------------------|
| Pact Broker UI  | http://localhost:9292  |
| Jenkins         | http://localhost:8080  |
| Pact Dashboard  | http://localhost:3000  |
| Order Service   | http://localhost:5000  |
| User Service    | http://localhost:5001  |
| Product Service | http://localhost:5002  |

Credentials везде: admin / admin

## Workflow
1. Запусти Jenkins job "01-consumer-pact-tests"
2. Запусти "02-provider-user-verify" и "03-provider-product-verify"
3. Открой Pact Broker UI — посмотри матрицу
4. Открой Pact Dashboard — посмотри граф зависимостей
5. Попробуй сломать контракт (см. секцию Demo)

## Demo: Breaking Contract
...
```

---

## Важные требования к реализации

1. **Все контейнеры** должны иметь `healthcheck` и `depends_on` с `condition: service_healthy`
2. **Jenkins jobs** должны создаваться автоматически через JCasC — никакого ручного создания
3. **Pact Broker** должен быть доступен по `http://localhost:9292` с UI
4. **pact-dashboard** использует nginx proxy для запросов к Broker — CORS проблем быть не должно
5. **Все скрипты** в `scripts/` должны быть исполняемыми (`chmod +x`)
6. **`app_broken.py`** обязательно включить для демонстрации смысла Pact
7. **React компоненты** используют только зависимости из package.json — никаких CDN
8. Если `pact-python` требует Ruby runtime для mock service — установить в Dockerfile
9. Вся конфигурация через environment variables — никаких hardcoded URL в коде сервисов
10. После `docker-compose up` система должна работать без дополнительных шагов

---

## Недостающие файлы — обязательно создай их тоже

### `pact-dashboard/vite.config.js`

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/broker': {
        target: 'http://pact-broker:9292',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api\/broker/, ''),
        headers: {
          Authorization: 'Basic YWRtaW46YWRtaW4=',
          Accept: 'application/hal+json',
        },
      },
    },
  },
});
```

### `pact-dashboard/src/main.jsx`

```jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### `pact-dashboard/index.html`

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Pact Dashboard</title>
    <style>
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { background: #0f172a; }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

### `pact-dashboard/src/components/VerificationTimeline.jsx`

```jsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function VerificationTimeline({ matrix }) {
  if (!matrix) return null;

  // Группируем верификации по дате
  const rows = matrix.matrix || [];
  const byDate = {};
  rows.forEach(row => {
    const date = row.verificationResult?.verifiedAt
      ? new Date(row.verificationResult.verifiedAt).toLocaleDateString()
      : null;
    if (!date) return;
    if (!byDate[date]) byDate[date] = { date, passed: 0, failed: 0 };
    if (row.verificationResult?.success) byDate[date].passed++;
    else byDate[date].failed++;
  });

  const data = Object.values(byDate).sort((a, b) => new Date(a.date) - new Date(b.date));

  return (
    <div style={{ background: '#1e293b', borderRadius: 16, border: '1px solid #334155', overflow: 'hidden', marginTop: 24 }}>
      <div style={{ padding: '20px 24px', borderBottom: '1px solid #334155' }}>
        <h2 style={{ margin: 0, fontSize: 18, color: '#f1f5f9' }}>Verification Timeline</h2>
        <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: 14 }}>History of contract verifications over time</p>
      </div>
      <div style={{ padding: 24 }}>
        {data.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#475569' }}>No verification history yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#f1f5f9' }}
              />
              <Legend />
              <Line type="monotone" dataKey="passed" stroke="#4ade80" strokeWidth={2} dot={{ fill: '#4ade80' }} name="Passed" />
              <Line type="monotone" dataKey="failed" stroke="#f87171" strokeWidth={2} dot={{ fill: '#f87171' }} name="Failed" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
```

Добавь `VerificationTimeline` в `App.jsx` — он рендерится под матрицей на вкладке `matrix`:
```jsx
// В секции {tab === 'matrix' && ...}:
{tab === 'matrix' && (
  <>
    <CompatibilityMatrix matrix={matrix} />
    <VerificationTimeline matrix={matrix} />
  </>
)}
```

---

### `provider-user/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

### `provider-product/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

---

### `scripts/verify-provider-product.sh`

```bash
#!/bin/bash
set -e
echo "=== Verifying product-service ==="
pact-verifier \
  --provider-base-url=http://localhost:5002 \
  --provider-states-setup-url=http://localhost:5002/pact-setup \
  --pact-broker-base-url=http://localhost:9292 \
  --broker-username=admin \
  --broker-password=admin \
  --provider=product-service \
  --provider-app-version=1.0.0 \
  --publish-verification-results
echo "✅ product-service verified!"
```

---

### `jenkins/jenkins-config/plugins.txt` — финальная версия

Убедись что файл содержит именно эти плагины (без версий — Jenkins скачает последние совместимые):

```
configuration-as-code
workflow-aggregator
workflow-job
git
pipeline-stage-view
docker-workflow
credentials-binding
ansicolor
job-dsl
```

Плагин `job-dsl` обязателен — без него JCasC не сможет создать jobs через Groovy DSL.

---

### `.gitignore`

```
# Python
__pycache__/
*.py[cod]
venv/
.env
consumer/pacts/
consumer/logs/

# Node
node_modules/
dist/

# Docker
.docker/

# Jenkins
jenkins_home/

# IDE
.idea/
.vscode/
*.iml
```

---

### `consumer/Dockerfile` — финальная версия с правильной установкой pact-mock_service

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Ruby нужен для pact-mock_service (используется pact-python под капотом)
RUN apt-get update && apt-get install -y \
    curl \
    ruby \
    ruby-dev \
    build-essential \
    && gem install pact-mock_service --no-document \
    && rm -rf /var/lib/apt/lists/*

# pact-broker CLI (для publish и can-i-deploy)
RUN gem install pact_broker-client --no-document

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# При запуске контейнера — стартуем Flask приложение
CMD ["python", "app.py"]
```

---

## Порядок проверки после запуска

```bash
# 1. Проверить что все контейнеры запустились
docker-compose ps

# 2. Проверить Pact Broker
curl http://localhost:9292/diagnostic/status/heartbeat

# 3. Запустить consumer тесты и опубликовать контракты
docker-compose exec consumer bash -c "cd /app && pytest tests/ -v"

# 4. Верифицировать провайдеров
bash scripts/verify-provider-user.sh
bash scripts/verify-provider-product.sh

# 5. Открыть Dashboard
open http://localhost:3000
open http://localhost:9292
open http://localhost:8080
```

---

## Известные проблемы и как их решать

### pact-python и Ruby
`pact-python` версии 1.x использует `pact-mock_service` (Ruby gem) под капотом.
Если возникнет ошибка `pact-mock_service not found` — в consumer Dockerfile уже есть установка.
Альтернатива — использовать `pact-python>=2.0` (Go binary, Ruby не нужен):
```dockerfile
# Убери Ruby из Dockerfile consumer, оставь только:
RUN pip install pact-python --pre
```

### React Flow — правильное имя пакета
`react-flow-renderer` устарел. Используй актуальный пакет:
```json
"reactflow": "^11.10.0"
```
```jsx
import ReactFlow, { Background, Controls, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';
```

### Jenkins первый запуск
Jenkins при первом старте занимает 2-3 минуты.
Если jobs не появились — `docker-compose restart jenkins`
Лог JCasC: `docker-compose logs jenkins | grep -i casc`
Плагин `job-dsl` обязателен для создания jobs через `jenkins.yaml`.

### CORS в nginx
Если Broker возвращает CORS ошибки — расширь `nginx.conf`:
```nginx
location /api/broker/ {
    proxy_pass http://pact-broker:9292/;
    proxy_set_header Host pact-broker:9292;
    proxy_set_header Authorization "Basic YWRtaW46YWRtaW4=";
    proxy_set_header Accept "application/hal+json, application/json";
    add_header Access-Control-Allow-Origin "*" always;
    add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
    if ($request_method = OPTIONS) { return 204; }
}
```

---

## Итоговый чеклист файлов

После генерации убедись что все файлы существуют:

```
pact-poc/
├── .gitignore
├── docker-compose.yml
├── README.md
├── consumer/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   └── tests/
│       ├── conftest.py
│       ├── test_user_pact.py
│       └── test_product_pact.py
├── provider-user/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
├── provider-product/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   └── app_broken.py          ← ОБЯЗАТЕЛЬНО для демо
├── pact-dashboard/
│   ├── Dockerfile
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/brokerApi.js
│       └── components/
│           ├── DependencyGraph.jsx
│           ├── CompatibilityMatrix.jsx
│           ├── ContractList.jsx
│           └── VerificationTimeline.jsx
├── jenkins/
│   ├── Dockerfile
│   ├── jenkins-config/
│   │   ├── plugins.txt
│   │   └── jenkins.yaml
│   └── pipelines/
│       ├── Jenkinsfile.consumer
│       ├── Jenkinsfile.provider-user
│       └── Jenkinsfile.provider-product
└── scripts/
    ├── publish-pacts.sh
    ├── verify-provider-user.sh
    ├── verify-provider-product.sh
    └── can-i-deploy.sh
```

Если какой-то файл отсутствует — создай его явно перед завершением.
