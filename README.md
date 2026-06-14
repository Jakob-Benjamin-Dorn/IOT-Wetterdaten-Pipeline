# IoT-Wetterdaten-Pipeline

[![CI](https://github.com/Jakob-Benjamin-Dorn/IOT-Wetterdaten-Pipeline/actions/workflows/tests.yml/badge.svg)](https://github.com/Jakob-Benjamin-Dorn/IOT-Wetterdaten-Pipeline/actions/workflows/tests.yml)

Portfolio-Projekt für eine kleine IoT-Wetterstation mit lokalem Entwicklungsstack und AWS-Cloud-Ingestion.

Ein ESP32-C6-Zero-Microcontroller mit angeschlossenem BME280-Sensor misst Temperatur, Luftfeuchtigkeit und Luftdruck und versendet über ein WLAN-Modul die Messwerte per HTTP. Im lokalen Setup nimmt ein FastAPI-Collector die Messwerte entgegen, speichert die Raw JSON S3-kompatibel in LocalStack und schreibt validierte Messwerte zusätzlich in PostgreSQL. Grafana visualisiert die Messwerte aus PostgreSQL.

Im Cloud-Setup mit AWS ist derselbe fachliche Datenfluss als schlanke Serverless-/Dev-Architektur umgesetzt: der ESP32 sendet an eine stabile HTTPS-Domain, API-Gateway leitet an eine Lambda weiter, die Lambda validiert die Payload, prüft einen Header-Token, speichert den vollständige Raw-Payload in Amazon S3 und schreibt normalisierte Werte nach Amazon RDS PostgreSQL. Eine zweite Lambda wird per EventBridge Scheduler regelmäßig ausgeführt und schreibt bei veralteten Sensordaten OpenWeather-Fallback-Werte über denselben Collector-Pfad. Grafana läuft als eigenes Docker-Image aus Amazon ECR auf einer EC2-Instanz und wird per SSM-Port-Forwarding geöffnet. Das Grafana-Image wird per GitHub Actions über OIDC nach ECR gepusht und die EC2 anschließend per SSM neu gestartet.

## Highlights

* eigener ESP32-C6-Zero mit BME280 als Datenquelle
* lokaler Entwicklungsstack mit FastAPI, PostgreSQL, LocalStack S3 und Grafana
* AWS-Cloud-Ingestion über API Gateway, Lambda, S3 und RDS PostgreSQL
* stabile Sensor-Domain für den ESP32 statt wechselnder API-Gateway-URL
* OpenWeather-Fallback bei fehlenden oder veralteten Sensordaten
* Grafana-Dashboard lokal und in AWS
* eigenes Grafana-Docker-Image mit Dashboard-Provisioning
* GitHub Actions CI für Tests
* GitHub Actions Deployment für Grafana-Image per AWS OIDC, ECR und SSM
* Terraform mit getrenntem Bootstrap- und Dev-Stack
* Remote Terraform State in S3 mit Locking
* AWS Budget Alert, API Gateway Throttling und Lambda Reserved Concurrency als Dev-Kosten- und Missbrauchsschutz
* Collector-Token und OpenWeather-Konfiguration über SSM Parameter Store statt Klarwerten in Lambda-Environment-Variablen

## Architektur

### Lokaler Datenfluss

```text
ESP32-C6-Zero + BME280
        ↓ HTTP POST
FastAPI Collector
        ├── Raw JSON → LocalStack S3
        └── validierte Messwerte → PostgreSQL
                                      ↓
                                   Grafana
```

Lokaler OpenWeather-Fallback:

```text
OpenWeather API
        ↓ Fallback-Skript
FastAPI Collector
        ├── Raw JSON → LocalStack S3
        └── validierte Messwerte → PostgreSQL
                                      ↓
                                   Grafana
```

### AWS-Datenfluss

```text
ESP32-C6-Zero + BME280
        ↓ HTTPS POST mit X-Collector-Token
https://sensor-domain-jakob.click/sensor-readings
        ↓
API Gateway HTTP API
        ↓ Lambda Proxy Integration
Lambda Collector
        ├── Raw JSON → Amazon S3 Raw Bucket
        └── normalisierte Messwerte → Amazon RDS PostgreSQL
                                             ↓
                                      Grafana auf EC2
                                      Zugriff per SSM-Port-Forwarding
```

Token-geschützter Leseendpunkt für Smoke-Tests und Debugging:

```text
GET /latest-readings
        ↓
Lambda Collector
        ↓
Amazon RDS PostgreSQL
```

Cloud-Fallback:

```text
EventBridge Scheduler
        ↓
Fallback-Lambda
        ├── prüft letzten Sensorwert über GET /latest-readings?source=sensor&limit=1
        └── schreibt bei Bedarf OpenWeather-Werte über POST /fallback-readings
```

Die Fallback-Lambda läuft bewusst ohne VPC-Anbindung, damit sie OpenWeather direkt über das Internet abrufen kann, ohne einen NAT Gateway zu benötigen. Die Collector-Lambda läuft in privaten Subnets, damit sie RDS erreichen kann. Für den Zugriff auf SSM Parameter Store nutzt die Collector-Lambda einen VPC Interface Endpoint.

## Repository-Struktur

```text
src/collector/
├── main.py                     # FastAPI-Adapter für den lokalen HTTP-Collector
├── lambda_handler.py           # Lambda-Adapter für den AWS-Cloud-Ingestion-Pfad
├── fallback_lambda_handler.py  # Cloud-Fallback über OpenWeather und bestehenden Collector-Pfad
├── parameter_store.py          # Runtime-Zugriff auf SSM Parameter Store
├── raw_storage.py              # S3-Raw-Speicherung ohne PostgreSQL-Abhängigkeit
├── rds_storage.py              # Cloud-RDS-Speicherung und Read-Zugriff
├── ingestion.py                # lokale Ingestion: S3 Raw JSON + PostgreSQL
├── models.py                   # Pydantic-Validierung der Messwerte
├── database.py                 # PostgreSQL-Zugriff lokal
├── config.py                   # zentrale Laufzeitkonfiguration über ENV-Variablen
├── fallback.py                 # testbare Fallback-Entscheidungslogik
└── exceptions.py               # projektspezifische Exceptions

scripts/dev/
├── send-test-reading.sh
├── send-fallback-reading.sh
├── show-latest-readings.sh
├── list-raw-objects.sh
└── smoke-test-local-stack.sh

scripts/fallback/
├── fetch-openweather-reading.py
├── check-and-fetch-fallback.py
└── run-fallback-check-loop.sh

scripts/cloud/
├── send-cloud-test-reading.sh
├── list-cloud-raw-objects.sh
├── show-latest-readings.sh
├── build-push-grafana-image.sh
├── restart-grafana-from-ecr.sh
└── open-grafana-tunnel.sh

infra/bootstrap/
└── langlebige Basisinfrastruktur: Remote State, ECR, GitHub OIDC, Budget, Domain

infra/dev/
└── zerstörbare Dev-Infrastruktur: API Gateway, Lambda, S3, RDS, Grafana EC2, Scheduler

.github/workflows/
├── tests.yml
└── deploy-grafana-image.yml

docker/grafana/
├── Dockerfile
└── provisioning/dashboards/dashboards.yml

grafana/dashboards/
└── iot-wetterstation.json

hardware/esp32-wetterstation/
├── esp32-wetterstation.ino
└── secrets.example.h

tests/
└── Unit-Tests für Validierung, Fallback, Lambda-Adapter und Ingestion
```

## Aktueller Projektstand

Bereits umgesetzt:

* ESP32 sendet Messwerte per HTTP POST lokal und in die AWS-Cloud.
* Der ESP32-Sketch kann über `USE_CLOUD` zwischen lokalem Collector und Cloud-Endpunkt umschalten.
* Der Cloud-Endpunkt nutzt eine stabile Domain: `https://sensor-domain-jakob.click/sensor-readings`.
* FastAPI nimmt Messwerte lokal entgegen.
* Der Collector akzeptiert `/readings` und `/sensor-readings`.
* Messwerte werden mit Pydantic validiert.
* Rohdaten werden lokal in LocalStack S3 und in AWS in einem echten S3 Raw Bucket gespeichert.
* Normalisierte Messwerte werden lokal in PostgreSQL und in AWS in Amazon RDS PostgreSQL gespeichert.
* Die Datenquelle wird über die Spalte `source` unterschieden: `sensor` oder `openweather`.
* OpenWeather-Fallback ist lokal und in der Cloud angebunden.
* Cloud-Fallback läuft über EventBridge Scheduler und eine eigene Fallback-Lambda.
* Grafana wird lokal per Docker Compose gestartet.
* Grafana läuft in AWS auf EC2 als Container aus einem eigenen ECR-Image.
* PostgreSQL-Datenquelle und Dashboard werden in Grafana provisioniert.
* Cloud-Grafana ist nicht öffentlich erreichbar, sondern wird per SSM-Port-Forwarding geöffnet.
* GitHub Actions führt Unit-Tests bei Push/Pull Request aus.
* GitHub Actions baut das Grafana-Image, pusht es per OIDC nach ECR und startet Grafana auf EC2 per SSM neu.
* Terraform verwaltet die AWS-Infrastruktur.
* Bootstrap- und Dev-Infrastruktur sind getrennt.
* Terraform State liegt remote in einem privaten S3 Backend mit Locking.
* ECR, GitHub OIDC, Budget und Domain gehören zur Bootstrap-Infrastruktur.
* API Gateway Throttling und Lambda Reserved Concurrency sind als Kosten-/Missbrauchsschutz gesetzt.
* Collector-Token und OpenWeather-Konfiguration liegen in SSM Parameter Store; Terraform verwaltet nur Parameternamen und IAM-Rechte.
* Der ESP32-Sketch enthält einfache Recovery-Logik für WLAN-/HTTP-Ausfälle.

Noch nicht umgesetzt:

* Quarantine-Ablage für ungültige oder unerwartete Payloads
* öffentliches Read-only-Grafana oder statischer Demo-Zugriff über `grafana.<domain>`
* vollständige Verlagerung von RDS- und Grafana-Passwörtern in Secrets Manager oder Parameter Store
* GitHub Actions für On-Demand-Aufbau und Zerstörung der gesamten Dev-Infrastruktur
* Export bereinigter Sample-Daten aus S3 für Reviewer ohne Zugriff auf die Live-Cloud
* Rebuild-Skript, das normalisierte RDS-Daten aus S3 Raw-Daten wiederherstellt
* AWS IoT Core / MQTT

AWS IoT Core und MQTT sind bewusst nur als mögliche Future Work vorgesehen. Der aktuelle Stand bleibt absichtlich HTTP-basiert, damit der Datenfluss leicht nachvollziehbar bleibt.

## Hardware

Board:

```text
Waveshare ESP32-C6-Zero
```

Sensor:

```text
BME280
```

Gemessene Werte:

```text
Temperatur
Luftfeuchtigkeit
Luftdruck
```

Verbindung:

```text
I²C
```

Aktuell funktionierende Pins:

```text
SDA → GPIO 4
SCL → GPIO 5
VCC → 3V3
GND → GND
```

Der Sensor sendet für die Demo typischerweise ungefähr alle 60 Sekunden. Das Intervall wird im ESP32-Sketch über `SEND_INTERVAL_MS` gesteuert.

## Erwartetes Sensor-JSON

Der Collector erwartet aktuell dieses Format:

```json
{
  "device_id": "esp32-c6-window-01",
  "temperature_c": 24.74,
  "humidity_pct": 38.12,
  "pressure_hpa": 1011.27
}
```

Gültigkeitsbereiche:

```text
temperature_c: -20 bis 50
humidity_pct: 0 bis 100
pressure_hpa: 800 bis 1200
```

Ungültige Werte werden abgelehnt und nicht in PostgreSQL gespeichert.

# Lokale Entwicklung

## Voraussetzungen

Benötigt:

* Python 3
* pip
* Docker
* Docker Compose
* optional: AWS CLI für lokale S3-Prüfungen
* optional: OpenWeather API-Key für echte Fallback-Daten

LocalStack wird über Docker Compose gestartet. Eine separat installierte LocalStack-CLI ist für den normalen lokalen Start nicht nötig.

## Python-Abhängigkeiten installieren

Optional mit virtueller Umgebung:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ohne virtuelle Umgebung:

```bash
python3 -m pip install --user -r requirements.txt
```

Die `.venv` ist nur eine lokale Python-Umgebung und gehört nicht ins Git-Repository.

## Umgebungsvariablen lokal

Aus Vorlage erstellen:

```bash
cp .env.example .env
```

Wichtige Beispielwerte:

```env
# LocalStack dummy credentials
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=eu-central-1

# S3 bucket for raw sensor payloads
RAW_BUCKET=weather-raw

# Local collector
COLLECTOR_HOST=0.0.0.0
COLLECTOR_PORT=8088

# PostgreSQL for host-side scripts.
# The collector container uses wetter-postgres:5432 internally.
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=weather
POSTGRES_USER=weather
POSTGRES_PASSWORD=weather

# OpenWeather fallback source
# Do not commit exact private coordinates or real API keys.
OPENWEATHER_API_KEY=your_api_key_here
OPENWEATHER_LAT=your_latitude_here
OPENWEATHER_LON=your_longitude_here

FALLBACK_THRESHOLD_SECONDS=120
FALLBACK_CHECK_INTERVAL_SECONDS=60
```

Die Datei `.env` wird nicht committed. Die LocalStack-Zugangsdaten `test/test` sind lokale Dummy-Werte und gehören nicht zu einem echten AWS-Account.

Wichtig: Terraform liest `.env` nicht automatisch. Für Terraform werden Variablen über `terraform.tfvars`, `*.auto.tfvars`, `-var=...` oder Umgebungsvariablen mit dem Prefix `TF_VAR_` gesetzt.

## Lokalen Stack starten

```bash
docker compose up -d postgres localstack grafana collector
```

Falls man den LocalStack-Token nicht in `.env` eintragen möchte:

```bash
export LOCALSTACK_AUTH_TOKEN=<dein-token>
docker compose up -d postgres localstack grafana collector
```

Prüfen:

```bash
docker compose ps
```

Collector-Logs:

```bash
docker logs -f wetter-collector
```

Health Check:

```bash
curl http://localhost:8088/health
```

Erwartete Antwort:

```json
{"status":"ok"}
```

## Lokalen Stack testen

```bash
set -a
source .env
set +a

./scripts/dev/smoke-test-local-stack.sh
```

Der Smoke-Test prüft:

1. Collector Health Check
2. Senden einer Testmessung
3. Sichtbarkeit der Messung in PostgreSQL
4. Sichtbarkeit eines Raw-Objekts in LocalStack S3

## Optional: Collector manuell starten

Für Debugging kann der Collector auch weiterhin manuell mit Uvicorn gestartet werden. Dann darf aber kein Collector-Container auf Port `8088` laufen.

```bash
docker compose up -d postgres localstack grafana
docker compose stop collector

set -a
source .env
set +a

uvicorn src.collector.main:app --host 0.0.0.0 --port 8088 --reload
```

## Lokale Testdaten senden

```bash
./scripts/dev/send-test-reading.sh
```

Alternativ per curl:

```bash
curl -X POST http://localhost:8088/readings \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-device-01",
    "temperature_c": 22.5,
    "humidity_pct": 45.0,
    "pressure_hpa": 1013.2
  }'
```

## PostgreSQL prüfen

```bash
./scripts/dev/show-latest-readings.sh
```

Oder direkt:

```bash
docker exec -it wetter-postgres psql -U weather -d weather -c \
"SELECT id, source, device_id, received_at, temperature_c, humidity_pct, pressure_hpa
 FROM weather_readings
 ORDER BY id DESC
 LIMIT 10;"
```

## LocalStack S3 prüfen

```bash
set -a
source .env
set +a

./scripts/dev/list-raw-objects.sh
```

Oder direkt:

```bash
AWS_ACCESS_KEY_ID=test \
AWS_SECRET_ACCESS_KEY=test \
AWS_DEFAULT_REGION=eu-central-1 \
aws --endpoint-url=http://localhost:4566 \
  s3 ls s3://weather-raw --recursive
```

Neue Raw-Objekte werden nach Quelle und Gerät partitioniert:

```text
raw_readings/source=sensor/device_id=esp32-c6-window-01/year=2026/month=06/day=12/hour=10/...
raw_readings/source=openweather/device_id=openweather-reference/year=2026/month=06/day=12/hour=10/...
```

## OpenWeather-Fallback lokal

Einen einzelnen OpenWeather-Wert abrufen und an den Collector senden:

```bash
set -a
source .env
set +a

./scripts/fallback/fetch-openweather-reading.py
```

Fallback nur dann auslösen, wenn der letzte Sensorwert zu alt ist:

```bash
./scripts/fallback/check-and-fetch-fallback.py
```

Fallback-Prüfung regelmäßig ausführen:

```bash
./scripts/fallback/run-fallback-check-loop.sh
```

OpenWeather-Werte werden mit `source = openweather` gespeichert. Sensorwerte werden mit `source = sensor` gespeichert.

## Tests

```bash
pytest
```

Die Tests prüfen unter anderem:

* Pydantic-Validierung der Messwerte
* Fallback-Entscheidungslogik
* zentrale Konfiguration
* S3-Key-Struktur
* Lambda-Adapter ohne echten AWS-Aufruf
* token-geschützte Lambda-Routen für Schreiben und Lesen
* Cloud-Fallback-Entscheidung und OpenWeather-Ingestion-Pfad

Die Tests benötigen keine laufenden Docker-Container.

## Grafana lokal öffnen

```text
http://localhost:3000
```

Login lokal:

```text
Benutzer: admin
Passwort: admin
```

Das lokale Dashboard heißt:

```text
IoT-Wetterstation
```

Die PostgreSQL-Datenquelle wird automatisch provisioniert:

```text
Wetter PostgreSQL
```

Beispielquery:

```sql
SELECT
  received_at AS "time",
  temperature_c AS "Temperatur °C"
FROM weather_readings
WHERE source = 'sensor'
ORDER BY received_at;
```

# ESP32

Der Sketch liegt unter:

```text
hardware/esp32-wetterstation/esp32-wetterstation.ino
```

Die Datei `secrets.h` liegt lokal im gleichen Ordner, enthält WLAN-Daten, URLs und den Cloud-Token und wird nicht committed. Als Vorlage dient:

```text
hardware/esp32-wetterstation/secrets.example.h
```

Wichtige Einstellung:

```cpp
#define USE_CLOUD false
```

Mit `false` sendet der ESP32 an den lokalen FastAPI-Collector. Mit `true` sendet er an den AWS-Cloud-Endpunkt.

Für lokale Tests muss die URL auf die LAN-IP des Rechners zeigen, nicht auf `localhost`:

```cpp
#define LOCAL_COLLECTOR_URL "http://192.168.0.248:8088/sensor-readings"
```

Für Cloud-Tests wird die stabile Sensor-Domain verwendet:

```cpp
#define CLOUD_COLLECTOR_URL "https://sensor-domain-jakob.click/sensor-readings"
```

Der Cloud-Endpunkt erwartet zusätzlich diesen Header:

```text
X-Collector-Token: <token>
```

Der Token steht lokal in `secrets.h` als `CLOUD_COLLECTOR_TOKEN`. Er ist kein AWS-Zugangsschlüssel und darf nicht ins Git-Repository.

# AWS Deployment

## Deployment-Überblick

Die AWS-Infrastruktur ist bewusst in zwei Terraform-Stacks getrennt:

```text
infra/bootstrap
  → langlebige Basisressourcen
  → wird selten geändert
  → sollte nicht regelmäßig zerstört werden

infra/dev
  → eigentliche Dev-/Demo-Umgebung
  → kann bei Bedarf neu gebaut oder zerstört werden
```

Diese Trennung ist wichtig, weil die Sensor-Domain, das ECR Repository, das GitHub-OIDC-Setup und der Terraform-State unabhängig von der temporären Dev-Umgebung bleiben sollen.

## AWS-Profil setzen

Für echte AWS-Befehle nicht die lokale `.env` mit LocalStack-Dummy-Credentials sourcen. Stattdessen:

```bash
unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY
unset AWS_SESSION_TOKEN

export AWS_PROFILE=iot-dev
aws sts get-caller-identity --profile iot-dev
```

Falls nötig vorher SSO Credentials in AWS IAM Identity Center konfigurieren, anschließend einloggen mit:

```bash
aws sso login --profile iot-dev
```

## Bootstrap-Infrastruktur

Bootstrap enthält:

* privaten S3 Bucket für Remote Terraform State
* State Locking über S3 Lockfile
* ECR Repository für das Grafana-Image
* GitHub OIDC Provider und IAM-Rolle für Grafana-Deployment
* AWS Budget Alert für die Dev-Umgebung
* Route 53 / ACM / API Gateway Custom Domain für den stabilen Sensoreingang

Typischer Ablauf:

```bash
cd infra/bootstrap
export AWS_PROFILE=iot-dev

terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

Wichtige Outputs:

```bash
terraform output grafana_ecr_repository_url
terraform output github_actions_grafana_role_arn
terraform output sensor_api_url
```

Der ESP32 nutzt als stabile Zieladresse:

```text
https://sensor-domain-jakob.click/sensor-readings
```

## Dev-Infrastruktur

Dev enthält:

* VPC, private Subnets und Security Groups
* API Gateway HTTP API
* API Mapping auf die stabile Sensor-Domain
* Collector-Lambda
* Fallback-Lambda
* EventBridge Scheduler
* S3 Raw Bucket
* RDS PostgreSQL
* EC2-Instanz für Grafana
* IAM-Rollen und Policies
* VPC Interface Endpoint für SSM Parameter Store Zugriff aus der Collector-Lambda

Vor `terraform plan/apply` müssen die noch lokal verwalteten Secrets als Terraform-Variablen gesetzt sein. Aktuell betrifft das insbesondere RDS- und Grafana-Passwörter:

```bash
cd infra/dev
export AWS_PROFILE=iot-dev

export TF_VAR_db_password="<rds-password>"
export TF_VAR_grafana_admin_password="<grafana-admin-password>"
```

Collector-Token und OpenWeather-Konfiguration liegen in SSM Parameter Store. Terraform braucht dafür nur die Parameternamen. Die Default-Namen sind:

```text
/iot-wetterdaten-pipeline/dev/collector-token
/iot-wetterdaten-pipeline/dev/openweather-api-key
/iot-wetterdaten-pipeline/dev/openweather-lat
/iot-wetterdaten-pipeline/dev/openweather-lon
```

Parameter bei Bedarf setzen oder aktualisieren:

```bash
aws ssm put-parameter \
  --name "/iot-wetterdaten-pipeline/dev/collector-token" \
  --type "SecureString" \
  --value "<collector-token>" \
  --overwrite \
  --profile iot-dev

aws ssm put-parameter \
  --name "/iot-wetterdaten-pipeline/dev/openweather-api-key" \
  --type "SecureString" \
  --value "<openweather-api-key>" \
  --overwrite \
  --profile iot-dev

aws ssm put-parameter \
  --name "/iot-wetterdaten-pipeline/dev/openweather-lat" \
  --type "String" \
  --value "<lat>" \
  --overwrite \
  --profile iot-dev

aws ssm put-parameter \
  --name "/iot-wetterdaten-pipeline/dev/openweather-lon" \
  --type "String" \
  --value "<lon>" \
  --overwrite \
  --profile iot-dev
```

Deploy der Dev-Infrastruktur:

```bash
cd infra/dev
export AWS_PROFILE=iot-dev

terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

Wichtige Outputs:

```bash
terraform output -raw collector_api_endpoint
terraform output -raw stable_sensor_api_url
terraform output -raw raw_bucket_name
terraform output -raw fallback_lambda_function_name
terraform output -raw grafana_instance_id
```

## Lambda-Paket aktualisieren

Wenn Python-Code für Collector oder Fallback geändert wurde:

```bash
pytest
./scripts/deploy/build-lambda-package.sh

cd infra/dev
terraform plan
terraform apply
```

Der Terraform-Plan zeigt dann typischerweise eine Änderung am `source_code_hash` der Lambdas.

## Cloud-Smoke-Test

Collector-Token lokal aus SSM holen:

```bash
export AWS_PROFILE=iot-dev
export COLLECTOR_TOKEN="$(
  aws ssm get-parameter \
    --name "/iot-wetterdaten-pipeline/dev/collector-token" \
    --with-decryption \
    --query 'Parameter.Value' \
    --output text \
    --profile iot-dev
)"
```

Testmessung senden und letzte Werte lesen:

```bash
./scripts/cloud/send-cloud-test-reading.sh
./scripts/cloud/show-latest-readings.sh
```

Direkt per curl gegen die stabile Domain:

```bash
curl -i -X POST "https://sensor-domain-jakob.click/sensor-readings" \
  -H "Content-Type: application/json" \
  -H "X-Collector-Token: $COLLECTOR_TOKEN" \
  -d '{
    "device_id": "domain-test-01",
    "temperature_c": 21.5,
    "humidity_pct": 45.0,
    "pressure_hpa": 1012.0
  }'
```

Erwartung:

```text
HTTP/2 202
```

Raw-Objekte im AWS-S3-Bucket prüfen:

```bash
./scripts/cloud/list-cloud-raw-objects.sh
```

Oder direkt:

```bash
aws s3 ls \
  s3://$(cd infra/dev && terraform output -raw raw_bucket_name)/raw_readings/ \
  --recursive \
  --profile iot-dev
```

## Cloud-Fallback testen

```bash
cd infra/dev
export AWS_PROFILE=iot-dev

aws lambda invoke \
  --function-name "$(terraform output -raw fallback_lambda_function_name)" \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/fallback-response.json \
  --profile iot-dev

cat /tmp/fallback-response.json | python3 -m json.tool
```

## Grafana-Image deployen

Normalerweise übernimmt GitHub Actions den Build und Push des Grafana-Images:

```text
.github/workflows/deploy-grafana-image.yml
```

Der Workflow:

1. checkt das Repository aus
2. übernimmt per GitHub OIDC eine AWS-Rolle
3. loggt sich in Amazon ECR ein
4. baut das Grafana-Docker-Image
5. pusht das Image mit Tag `latest`
6. findet die laufende Grafana-EC2 anhand von Tags
7. startet Grafana auf EC2 per SSM mit dem neuen Image neu

Dafür sind im GitHub Repository keine langfristigen AWS Access Keys nötig. Benötigte GitHub Repository Variables:

```text
AWS_REGION=eu-central-1
AWS_ROLE_ARN=<Output aus infra/bootstrap: github_actions_grafana_role_arn>
ECR_REPOSITORY=iot-wetterdaten-pipeline-dev-grafana
```

Lokal kann derselbe Build/Push-Prozess manuell ausgeführt werden:

```bash
export AWS_PROFILE=iot-dev
./scripts/cloud/build-push-grafana-image.sh
./scripts/cloud/restart-grafana-from-ecr.sh
```

## Cloud-Grafana öffnen

Grafana ist nicht öffentlich erreichbar. Zugriff erfolgt per SSM-Port-Forwarding:

```bash
export AWS_PROFILE=iot-dev
./scripts/cloud/open-grafana-tunnel.sh
```

Danach im Browser öffnen:

```text
http://localhost:3001
```

Die Datasource heißt:

```text
Wetter PostgreSQL
```

Das Dashboard heißt:

```text
IoT-Wetterstation
```

## Dev-Umgebung pausieren und fortsetzen

Für kurze Pausen kann die Infrastruktur stehen bleiben. Für Kostenkontrolle können RDS und EC2 gestoppt werden.

RDS stoppen:

```bash
aws rds stop-db-instance \
  --db-instance-identifier iot-wetterdaten-pipeline-dev-postgres \
  --profile iot-dev
```

EC2 stoppen:

```bash
cd infra/dev
aws ec2 stop-instances \
  --instance-ids "$(terraform output -raw grafana_instance_id)" \
  --profile iot-dev
```

RDS wieder starten:

```bash
aws rds start-db-instance \
  --db-instance-identifier iot-wetterdaten-pipeline-dev-postgres \
  --profile iot-dev
```

EC2 wieder starten:

```bash
cd infra/dev
aws ec2 start-instances \
  --instance-ids "$(terraform output -raw grafana_instance_id)" \
  --profile iot-dev
```

Anschließend warten, bis RDS `available` und die EC2 per SSM `Online` ist. Danach den Grafana-Tunnel erneut öffnen.

## Dev-Umgebung zerstören

```bash
cd infra/dev
export AWS_PROFILE=iot-dev

terraform plan -destroy
terraform destroy
```

Achtung: `terraform destroy` entfernt alle von `infra/dev` verwalteten Ressourcen. Dazu gehören API Gateway, Lambdas, RDS, Grafana-EC2 und der S3 Raw Bucket. Raw-Daten im S3 Bucket gehen verloren, sofern sie vorher nicht gesichert oder aus dem Destroy-Pfad herausgenommen wurden.

Bootstrap sollte nicht routinemäßig zerstört werden, weil dort Remote State, Domain, ECR, OIDC und Budget liegen.

# Sicherheit, Secrets und öffentlicher Betrieb des Projekts

Das Repository ist tauglich für den öffentlichen Zugriff, solange keine echten Secrets oder lokalen State-Dateien enthalten sind.

Nicht ins Repository gehören insbesondere:

```text
.env
terraform.tfvars
*.tfvars
terraform.tfstate
terraform.tfstate.*
.terraform/
hardware/esp32-wetterstation/secrets.h
```

Vor dem Veröffentlichen prüfen:

```bash
git status --ignored
git ls-files | grep -E '(\.env|tfstate|tfvars|secrets\.h)$' || true
```

Der Cloud-Endpunkt darf sichtbar sein. Der Schutz hängt am geheimen `X-Collector-Token`, an bewusst niedrig gesetztem API Gateway Throttling, Lambda Reserved Concurrency und einem AWS Budget Alert.

Aktueller Secret-Stand:

```text
SSM Parameter Store:
- Collector Token
- OpenWeather API Key
- OpenWeather Lat/Lon

Terraform-Variablen lokal:
- RDS Passwort
- Grafana Admin Passwort
```

Terraform verwaltet für Parameter Store nur die Parameternamen, IAM-Rechte und Lambda-Environment-Variablen mit Parameternamen. Die Secret-Werte selbst werden per AWS CLI oder Konsole gesetzt und sollen nicht im Terraform-State landen.

GitHub Actions verwendet OIDC statt langfristiger AWS Access Keys. Die vorhandene GitHub-OIDC-Rolle ist auf das Grafana-Deployment beschränkt. Ein späterer Terraform-Deploy/Destroy-Workflow sollte eine separate, enger geprüfte Rolle und GitHub Environment Approval verwenden.

Live-Daten aus der eigenen AWS-Umgebung sind nicht automatisch für Dritte sichtbar. Personen, die das Repository in ihrem eigenen AWS-Account deployen, erstellen ihre eigene Infrastruktur und sehen nur eigene Testdaten.

Ein öffentliches Read-only-Grafana unter eigener Domain ist möglich, aber nicht Teil des aktuellen sicheren Dev-Standes.

# Sample-Daten

Noch nicht enthalten. Als nächster Portfolio-Schritt sollen bereinigte Sample-Daten aus S3 exportiert werden, damit Reviewer den Datenfluss auch ohne Zugriff auf die Live-AWS-Umgebung nachvollziehen können.

Geplantes Ziel:

```text
sample-data/
├── raw/sensor/*.json
├── raw/openweather/*.json
└── normalized/weather_readings_sample.csv
```

Vor einem Export sollten die Raw-Payloads auf private Metadaten, exakte Koordinaten und sonstige sensible Informationen geprüft werden.

# Warum diese Komponenten?

| Komponente        | Zweck                                                        |
| ----------------- | ------------------------------------------------------------ |
| ESP32-C6 + BME280 | echte lokale Sensordaten                                     |
| FastAPI           | einfacher HTTP-Collector und lokaler Entwicklungsadapter     |
| Lambda            | serverloser Cloud-Collector                                  |
| API Gateway       | stabiler HTTPS-Eingang für Sensor und Smoke-Tests            |
| Route 53 / ACM    | stabile Sensor-Domain und TLS-Zertifikat                     |
| LocalStack S3     | lokales Raw-Datenarchiv                                      |
| Amazon S3         | Cloud-Raw-Datenarchiv                                        |
| PostgreSQL/RDS    | strukturierte Messwerte für Abfragen und Grafana             |
| Grafana           | Visualisierung der Messwerte                                 |
| Docker Compose    | reproduzierbarer lokaler Betrieb                             |
| Amazon ECR        | Registry für eigenes Grafana-Image                           |
| GitHub Actions    | Tests und Grafana-Image-Deployment                           |
| OpenWeather       | externe Referenz-/Fallback-Quelle bei Sensorausfall          |
| Terraform         | reproduzierbare Infrastruktur                                |

# Future Work

Mögliche spätere Erweiterungen:

* bereinigter Sample-Data-Export aus S3 und RDS
* On-Demand GitHub Actions für `infra/dev` Plan/Apply/Destroy mit Environment Approval
* öffentliches Read-only-Grafana oder statischer Demo-Zugang unter eigener Subdomain
* Quarantine-Prefix oder Quarantine-Bucket für ungültige Payloads
* vollständige Verlagerung von RDS- und Grafana-Passwörtern in Secrets Manager oder Parameter Store
* RDS-managed Master Password oder Secrets Manager Integration prüfen
* Rebuild-Skript, das normalisierte RDS-Daten aus S3 Raw-Daten wiederherstellt
* S3 Lifecycle Rules für Raw-Daten
* optionaler späterer Wechsel von EC2 zu ECS/Fargate oder ALB/CloudFront für eine öffentliche Demo
* RDS Proxy für robustere Lambda/RDS-Verbindungen bei höherer Last
* AWS IoT Core
* MQTT statt HTTP
* Device-Zertifikate
