# IoT-Wetterdaten-Pipeline

[![CI](https://github.com/Jakob-Benjamin-Dorn/IOT-Wetterdaten-Pipeline/actions/workflows/tests.yml/badge.svg)](https://github.com/Jakob-Benjamin-Dorn/IOT-Wetterdaten-Pipeline/actions/workflows/tests.yml)

Portfolio-Projekt für eine kleine IoT-Wetterstation mit lokalem Entwicklungsstack und erster AWS-Cloud-Ingestion.

Ein ESP32-C6-Zero mit BME280-Sensor misst Temperatur, Luftfeuchtigkeit und Luftdruck und sendet die Messwerte per HTTP. Lokal nimmt ein FastAPI-Collector die Messwerte entgegen, speichert die Rohdaten in einem S3-kompatiblen Raw-Archiv über LocalStack und legt die validierten Messwerte zusätzlich in PostgreSQL ab. Grafana visualisiert die Messwerte aus PostgreSQL.

Zusätzlich kann eine OpenWeather-basierte Fallback-Quelle genutzt werden, wenn längere Zeit keine aktuellen Sensordaten eintreffen. In AWS ist inzwischen ein schlanker Cloud-Ingestion-Pfad vorhanden: API Gateway nimmt HTTP-Requests entgegen, eine Lambda validiert die Messwerte, prüft einen Header-Token, speichert valide Raw-Payloads in einem echten S3 Raw Bucket und legt normalisierte Messwerte zusätzlich in Amazon RDS PostgreSQL ab. Eine zweite Lambda wird per EventBridge Scheduler regelmäßig ausgeführt und schreibt bei veralteten Sensordaten OpenWeather-Fallback-Werte über denselben Collector-Pfad. Grafana läuft in der Dev-Umgebung als eigenes Docker-Image aus Amazon ECR auf einer EC2-Instanz und wird per SSM-Port-Forwarding geöffnet. Das Grafana-Image wird per GitHub Actions über OIDC nach ECR gepusht und die EC2 anschließend per SSM neu gestartet.

## Aktueller Datenfluss

```text
ESP32-C6-Zero + BME280
        ↓ HTTP POST
FastAPI Collector
        ├── Raw JSON → LocalStack S3
        └── validierte Messwerte → PostgreSQL
                                      ↓
                                   Grafana

OpenWeather API
        ↓ lokales Fallback-Skript
FastAPI Collector
        ├── Raw JSON → LocalStack S3
        └── validierte Messwerte → PostgreSQL
                                      ↓
                                   Grafana
```

Aktueller Cloud-Pfad:

```text
ESP32-C6-Zero + BME280 / curl
        ↓ HTTP POST mit X-Collector-Token
API Gateway HTTP API
        ↓ Lambda Proxy Integration
Lambda Collector
        ├── Raw JSON → Amazon S3 Raw Bucket
        └── normalisierte Messwerte → Amazon RDS PostgreSQL
                                             ↓
                                      Grafana auf EC2
                                      Zugriff per SSM-Port-Forwarding
```

Token-geschützter Leseendpunkt für Debugging und Smoke-Tests:

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
        ├── prüft letzten Sensorwert über GET /latest-readings
        └── schreibt bei Bedarf OpenWeather-Werte über POST /fallback-readings
```

## Aktuelle Ordnerstruktur

```text
src/collector/
├── main.py            # FastAPI-Adapter für den lokalen HTTP-Collector
├── lambda_handler.py  # Lambda-Adapter für den AWS-Cloud-Ingestion-Pfad
├── fallback_lambda_handler.py  # Cloud-Fallback über OpenWeather und bestehenden Collector-Pfad
├── raw_storage.py     # S3-Raw-Speicherung ohne PostgreSQL-Abhängigkeit
├── rds_storage.py     # Cloud-RDS-Speicherung und Read-Zugriff für normalisierte Messwerte
├── ingestion.py       # lokale Ingestion: S3 Raw JSON + PostgreSQL
├── models.py          # Pydantic-Validierung der Messwerte
├── database.py        # PostgreSQL-Zugriff
├── config.py          # zentrale Laufzeitkonfiguration über ENV-Variablen
├── fallback.py        # testbare Fallback-Entscheidungslogik
└── exceptions.py      # projektspezifische Exceptions

scripts/dev/
├── send-test-reading.sh          # sendet künstliche Sensordaten
├── send-fallback-reading.sh      # sendet künstliche Fallback-Daten
├── show-latest-readings.sh       # zeigt letzte PostgreSQL-Zeilen
├── list-raw-objects.sh           # zeigt Raw-Objekte in LocalStack S3
└── smoke-test-local-stack.sh     # prüft Collector, PostgreSQL und S3 lokal zusammen

scripts/fallback/
├── fetch-openweather-reading.py  # ruft echte OpenWeather-Daten ab und postet sie an den Collector
├── check-and-fetch-fallback.py   # prüft, ob der Sensor zu alt ist, und löst ggf. OpenWeather aus
└── run-fallback-check-loop.sh    # führt die Fallback-Prüfung lokal regelmäßig aus

scripts/cloud/
├── send-cloud-test-reading.sh         # sendet eine Testmessung an API Gateway/Lambda
├── list-cloud-raw-objects.sh          # zeigt Raw-Objekte im echten AWS-S3-Bucket
├── show-latest-readings.sh            # liest die letzten normalisierten Messwerte aus RDS über Lambda
├── build-push-grafana-image.sh        # baut das Grafana-Image und pusht es nach ECR
├── restart-grafana-from-ecr.sh        # startet Grafana auf EC2 per SSM mit neuem ECR-Image neu
└── open-grafana-tunnel.sh             # öffnet Grafana lokal per SSM-Port-Forwarding

.github/workflows/
├── tests.yml                          # Unit-Tests
└── deploy-grafana-image.yml           # baut Grafana-Image, pusht nach ECR und startet EC2 per SSM neu

docker/grafana/
├── Dockerfile                         # eigenes Grafana-Image mit Dashboard-Provisioning
└── provisioning/dashboards/
    └── dashboards.yml                 # Dashboard-Provider für Grafana

hardware/esp32-wetterstation/
├── esp32-wetterstation.ino       # ESP32-C6/BME280-Sketch mit lokalem und Cloud-Ziel
└── secrets.example.h             # Vorlage für WLAN, URLs und Cloud-Token

infra/dev/
└── Terraform-Konfiguration für die aktuelle AWS-Dev-Umgebung

tests/
├── test_config.py
├── test_fallback.py
├── test_ingestion.py
├── test_lambda_handler.py
└── test_models.py
```

## Aktueller Projektstand

Bereits umgesetzt:

* ESP32 sendet Messwerte per HTTP POST lokal und optional in die AWS-Cloud.
* Der ESP32-Sketch kann über `USE_CLOUD` zwischen lokalem Collector und Cloud-Endpunkt umschalten.
* FastAPI nimmt Messwerte entgegen.
* Der Collector akzeptiert `/readings` und `/sensor-readings`.
* Messwerte werden validiert.
* Rohdaten werden lokal in LocalStack S3 gespeichert.
* Validierte Messwerte werden in PostgreSQL gespeichert.
* Die Datenquelle wird über die Spalte `source` unterschieden (`sensor`, `openweather`).
* Grafana wird lokal per Docker Compose gestartet.
* PostgreSQL-Datenquelle und Dashboard werden automatisch in Grafana provisioniert.
* OpenWeather-Fallback ist lokal angebunden.
* Eine lokale Fallback-Prüfung kann regelmäßig ausgeführt werden.
* Der Collector ist containerisiert.
* LocalStack, PostgreSQL, Grafana und Collector können gemeinsam per Docker Compose gestartet werden.
* Unit-Tests laufen mit `pytest`.
* GitHub Actions führt die Unit-Tests bei Push/Pull Request aus.
* Die Raw-S3-Speicherung ist von der PostgreSQL-Ingestion getrennt.
* Terraform verwaltet die aktuelle AWS-Dev-Umgebung.
* Ein echter S3 Raw Bucket ist in AWS angelegt.
* API Gateway und Lambda sind als Cloud-Ingestion-MVP deployed.
* Der Cloud-Endpunkt ist über `X-Collector-Token` abgesichert.
* Ein echter ESP32 kann Messwerte an API Gateway/Lambda senden, die im AWS-S3-Raw-Bucket landen.
* Amazon RDS PostgreSQL ist in der AWS-Dev-Umgebung angebunden.
* Die Cloud-Lambda läuft in einer VPC und schreibt valide Messwerte zusätzlich normalisiert nach RDS.
* RDS ist nicht öffentlich erreichbar; PostgreSQL-Zugriff ist per Security Group auf Lambda und Grafana beschränkt.
* Ein token-geschützter Read-Endpunkt `/latest-readings` kann die letzten normalisierten Messwerte aus RDS zurückgeben.
* Grafana läuft in AWS auf einer EC2-Instanz als Docker-Container.
* Das Grafana-Image wird als eigenes Image gebaut, in Amazon ECR abgelegt und von der EC2 gezogen.
* Der Zugriff auf Cloud-Grafana erfolgt per SSM-Port-Forwarding; Grafana ist nicht öffentlich erreichbar.
* Das bestehende Dashboard `grafana/dashboards/iot-wetterstation.json` wird im Grafana-Image provisioniert.
* Cloud-Fallback läuft über EventBridge Scheduler und eine zweite Lambda.
* Bei veralteten Sensordaten ruft die Fallback-Lambda OpenWeather ab und schreibt die Werte über denselben Collector-Pfad.
* GitHub Actions baut das Grafana-Image, pusht es per OIDC nach ECR und startet Grafana auf EC2 per SSM neu.
* Der ESP32-Sketch enthält einfache Recovery-Logik für WLAN-/HTTP-Ausfälle.

Noch nicht umgesetzt:

* Quarantine-Ablage für ungültige oder unerwartete Payloads
* API Gateway Throttling und Lambda Reserved Concurrency als Kosten-/Missbrauchsschutz
* AWS Budget Alert für die Dev-Umgebung
* Remote Terraform State Backend in S3 mit Locking
* Secrets Manager oder SSM Parameter Store für produktionsnähere Secret-Verwaltung
* stabile öffentliche Domain für den Sensor
* AWS IoT Core / MQTT

AWS IoT Core und MQTT sind bewusst nur als mögliche Future Work vorgesehen und werden in diesem Projekt zunächst nicht umgesetzt.

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

Ungültige Werte werden vom Collector abgelehnt und nicht in PostgreSQL gespeichert.

## Lokale Voraussetzungen

Benötigt:

* Python 3
* pip
* Docker
* Docker Compose
* optional: AWS CLI für lokale S3-Prüfungen
* optional: OpenWeather API-Key für echte Fallback-Daten

LocalStack wird inzwischen über Docker Compose gestartet. Eine separat lokal installierte LocalStack-CLI ist für den normalen Start nicht mehr nötig.

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

## Umgebungsvariablen

Aus Vorlage erstellen:

```bash
cp .env.example .env
```

Beispielwerte:

```env
# LocalStack dummy credentials
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=eu-central-1

# Optional: LocalStack token for Docker Compose
LOCALSTACK_AUTH_TOKEN=your_localstack_token_here

# LocalStack endpoint for host-side scripts.
# The collector container overrides this internally with http://localstack:4566.
LOCALSTACK_ENDPOINT=http://localhost:4566

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

# Fallback behavior
# Time without new sensor data until fallback is activated.
FALLBACK_THRESHOLD_SECONDS=120

# Time between fallback checks/fetches until sensor data arrives again.
FALLBACK_CHECK_INTERVAL_SECONDS=60
```

Die Datei `.env` wird nicht committed.

Die LocalStack-Zugangsdaten `test/test` sind lokale Dummy-Werte und gehören nicht zu einem echten AWS-Account. Echte OpenWeather-Koordinaten und API-Keys gehören ebenfalls nur in `.env`.

## Lokalen Stack starten

Der lokale Standardstart läuft über Docker Compose:

```bash
docker compose up -d postgres localstack grafana collector
```

Falls man den LocalStack-Token nicht in `.env` eintragen möchte, kann man ihn vor dem Start exportieren:

```bash
export LOCALSTACK_AUTH_TOKEN=<dein-token>
docker compose up -d postgres localstack grafana collector
```

Wichtig: Es sollte nicht gleichzeitig ein manuell gestarteter LocalStack-Prozess laufen, weil sonst Port `4566` bereits belegt ist.

Prüfen:

```bash
docker compose ps
```

Erwartung:

```text
wetter-postgres     running
wetter-localstack   running / healthy
wetter-grafana      running
wetter-collector    running
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

Nach dem Start kann ein lokaler Smoke-Test ausgeführt werden:

```bash
set -a
source .env
set +a

./scripts/dev/smoke-test-local-stack.sh
```

Der Funktions-Test prüft:

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

## Testdaten senden

Ohne echten Sensor:

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

Wenn AWS CLI installiert ist:

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

Neue Raw-Objekte werden nach Quelle und Gerät partitioniert, zum Beispiel:

```text
raw_readings/source=sensor/device_id=esp32-c6-window-01/year=2026/month=06/day=12/hour=10/...
raw_readings/source=openweather/device_id=openweather-reference/year=2026/month=06/day=12/hour=10/...
```

## OpenWeather-Fallback

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

Lokale Fallback-Prüfung regelmäßig ausführen:

```bash
./scripts/fallback/run-fallback-check-loop.sh
```

Aktuelle Logik:

```text
Wenn kein Sensorwert existiert:
    OpenWeather-Fallback auslösen

Wenn der letzte Sensorwert älter als FALLBACK_THRESHOLD_SECONDS ist:
    OpenWeather-Fallback auslösen

Wenn der Sensor wieder aktuelle Werte sendet:
    Fallback nicht weiter auslösen
```

OpenWeather-Werte werden mit `source = openweather` gespeichert. Sensorwerte werden mit `source = sensor` gespeichert.

## Tests

Unit-Tests ausführen:

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

## Grafana öffnen

Grafana läuft unter:

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

Das Dashboard zeigt Sensor- und OpenWeather-Werte unterscheidbar an. Wenn keine Daten angezeigt werden:

1. Prüfen, ob PostgreSQL Daten enthält.
2. Grafana-Zeitfenster auf `Last 6 hours` oder `Last 24 hours` setzen.
3. In Grafana Explore die Datenquelle `Wetter PostgreSQL` testen.

Beispielquery:

```sql
SELECT
  received_at AS "time",
  temperature_c AS "Temperatur °C"
FROM weather_readings
WHERE source = 'sensor'
ORDER BY received_at;
```

## Sensor-URL

Der ESP32 darf nicht an `localhost` senden, sondern an die LAN-IP des Rechners, auf dem der Collector läuft.

IP herausfinden:

```bash
hostname -I
```

Beispiel:

```text
http://192.168.0.123:8088/sensor-readings
```

Der Collector akzeptiert aktuell beide Pfade:

```text
/readings
/sensor-readings
```

## ESP32-Sketch lokal oder Cloud nutzen

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

Mit `false` sendet der ESP32 an den lokalen FastAPI-Collector. Mit `true` sendet er an API Gateway/Lambda in AWS.

Für lokale Tests muss die URL auf die LAN-IP des Rechners zeigen, nicht auf `localhost`:

```cpp
#define LOCAL_COLLECTOR_URL "http://192.168.0.248:8088/sensor-readings"
```

Für Cloud-Tests wird der API-Gateway-Endpunkt mit Pfad verwendet:

```cpp
#define CLOUD_COLLECTOR_URL "https://<api-id>.execute-api.eu-central-1.amazonaws.com/sensor-readings"
```

Der Cloud-Endpunkt erwartet zusätzlich diesen Header:

```text
X-Collector-Token: <token>
```

Der Token steht lokal in `secrets.h` als `CLOUD_COLLECTOR_TOKEN`. Er ist nicht identisch mit AWS-Zugangsdaten und darf nicht ins Git-Repository.


## Lokale Ports

| Dienst                    | Port |
| ------------------------- | ---: |
| FastAPI Collector         | 8088 |
| LocalStack                | 4566 |
| PostgreSQL Host-Port      | 5433 |
| PostgreSQL Container-Port | 5432 |
| Grafana                   | 3000 |

## Warum diese Komponenten?

| Komponente        | Zweck                                                        |
| ----------------- | ------------------------------------------------------------ |
| ESP32-C6 + BME280 | echte lokale Sensordaten                                     |
| FastAPI           | einfacher HTTP-Collector und lokaler Entwicklungsadapter     |
| Lambda-Adapter    | Vorbereitung für späteres API-Gateway/Lambda-Deployment      |
| LocalStack S3     | lokales Raw-Datenarchiv                                      |
| PostgreSQL        | strukturierte Messwerte für Abfragen                         |
| Grafana           | Visualisierung der Messwerte                                 |
| Docker Compose    | reproduzierbarer lokaler Betrieb des gesamten lokalen Stacks |
| OpenWeather       | externe Referenz-/Fallback-Quelle bei Sensorausfall          |

# Cloud-Zielarchitektur

## Ziel

Die lokale IoT-Wetterdaten-Pipeline soll schrittweise in AWS überführt werden, ohne den Sensor-Endpunkt unnötig oft ändern zu müssen. Grafana soll später nicht über Amazon Managed Grafana, sondern reproduzierbar als eigene Grafana-Instanz laufen.

## Stabiler Eintrittspunkt

Der ESP32 soll langfristig an eine stabile HTTPS-Adresse senden, zum Beispiel:

```text
https://sensor.example.com/sensor-readings
```

Diese Adresse sollte unabhängig davon bleiben, ob dahinter lokal FastAPI, später API Gateway + Lambda oder eine andere Collector-Implementierung läuft.

## Erste Cloud-Ausbaustufe

Für die erste Cloud-Version wird der HTTP-basierte Sensorpfad beibehalten:

```text
ESP32
→ stabile HTTPS-Adresse
→ API Gateway
→ Lambda Collector
→ S3 Raw Bucket
→ RDS PostgreSQL
```

Der vorbereitete Lambda-Adapter dient dazu, die gleiche Validierungs- und Ingestion-Logik später hinter API Gateway verwenden zu können.

## Grafana-Zielbild

Grafana ist von der Datenaufnahme getrennt.

Aktueller Dev-Stand:

```text
Grafana-Docker-Image
→ Amazon ECR
→ EC2-Instanz
→ PostgreSQL Datasource
→ Amazon RDS PostgreSQL
```

Der Zugriff auf Grafana erfolgt aktuell nicht öffentlich, sondern lokal per SSM-Port-Forwarding. Grafana liest die neuesten Daten aus RDS. Der Collector muss dafür nicht als dauerhaft laufender Container in AWS betrieben werden, weil die Datenaufnahme über API Gateway + Lambda erfolgt.

## Infrastruktur-Kategorien

### Bootstrap-Infrastruktur

Diese Infrastruktur sollte möglichst stabil bleiben und nicht regelmäßig zerstört werden:

* Domain / Route 53 Hosted Zone
* TLS-Zertifikate
* GitHub OIDC Provider
* Terraform State Backend
* ECR Repository für das Grafana-Image
* später eventuell feste DNS-Einträge für den Sensoreingang

### Umgebungsspezifische Infrastruktur

Diese Infrastruktur kann pro Umgebung aufgebaut, angepasst und bei Bedarf zerstört werden:

* API Gateway
* Lambda Collector
* S3 Raw Bucket
* RDS PostgreSQL
* ECS/EC2 für Grafana
* IAM Roles
* Security Groups
* CloudWatch Logs

S3 und RDS enthalten Daten und sollten trotz Terraform-Verwaltung nicht unbedacht gelöscht werden. Später sollten dafür Schutzmechanismen wie S3 Versioning, RDS Backups und bewusste Destroy-Regeln verwendet werden.

## Cloud-Ingestion MVP

Der AWS-Cloud-Pfad nimmt Wetterdaten per HTTP entgegen, speichert die vollständige Raw-Payload in S3 und legt die validierten Messwerte zusätzlich normalisiert in RDS PostgreSQL ab.

Datenfluss:

```text
curl / ESP32-C6 + BME280
  → API Gateway HTTP API
  → Lambda Collector
  → S3 Raw Bucket
  → RDS PostgreSQL
```

Der Endpunkt ist mit einem einfachen Header-Token geschützt:

```text
X-Collector-Token: <token>
```

Die Cloud-URL kann aus Terraform gelesen werden:

```bash
cd infra/dev
terraform output -raw collector_api_endpoint
```

Für Requests muss der Pfad ergänzt werden:

```text
/sensor-readings
```

Cloud-Smoke-Test:

```bash
export AWS_PROFILE=iot-dev
export COLLECTOR_TOKEN=<collector-token>

./scripts/cloud/send-cloud-test-reading.sh
./scripts/cloud/list-cloud-raw-objects.sh
./scripts/cloud/show-latest-readings.sh
```

Alternativ direkt prüfen:

```bash
aws s3 ls \
  s3://<raw-bucket-name>/raw_readings/ \
  --recursive \
  --profile iot-dev
```

Zusätzlich kann geprüft werden, ob der token-geschützte Read-Endpunkt normalisierte RDS-Daten liefert:

```bash
API_URL="$(cd infra/dev && terraform output -raw collector_api_endpoint)"

curl -sS -X GET "$API_URL/latest-readings" \
  -H "X-Collector-Token: $COLLECTOR_TOKEN" | python3 -m json.tool
```

## Cloud-Fallback mit OpenWeather

Der Cloud-Fallback läuft getrennt von Grafana und ohne dauerhaft laufenden Agenten auf der EC2-Instanz.

```text
EventBridge Scheduler
  → Fallback-Lambda
  → GET /latest-readings?source=sensor&limit=1
  → bei veraltetem Sensorwert: OpenWeather API
  → POST /fallback-readings
  → Collector-Lambda
  → S3 Raw Bucket + RDS PostgreSQL
```

Die Fallback-Lambda läuft nicht in der VPC. Dadurch kann sie OpenWeather direkt über das Internet abrufen, ohne einen NAT Gateway zu benötigen. Die eigentliche Speicherung bleibt trotzdem zentral im bestehenden Collector-Pfad. OpenWeather-Werte werden mit `source = openweather` gespeichert; echte Sensordaten mit `source = sensor`.

Der Scheduler wird aktuell über Terraform verwaltet und läuft in der Dev-Umgebung regelmäßig, typischerweise alle fünf Minuten. Der Schwellwert wird über `cloud_fallback_threshold_seconds` gesteuert.

Manueller Test:

```bash
cd infra/dev
export AWS_PROFILE=iot-dev

aws lambda invoke   --function-name "$(terraform output -raw fallback_lambda_function_name)"   --payload '{}'   /tmp/fallback-response.json   --profile iot-dev

cat /tmp/fallback-response.json | python3 -m json.tool
```

## RDS-Milestone: normalisierte Cloud-Messwerte

Amazon RDS PostgreSQL ist als Dev-Datenbank für normalisierte Cloud-Messwerte angebunden. Die Lambda schreibt nach erfolgreicher Validierung zuerst die vollständige Raw-Payload in S3 und danach eine normalisierte Zeile in die Tabelle `weather_readings`.

Aktueller Datenfluss:

```text
ESP32 / später OpenWeather
  → API Gateway / Lambda
  → S3 Raw Bucket
  → RDS PostgreSQL weather_readings
```

S3 bleibt die vollständige Raw-Ablage. RDS enthält nur die für Dashboard und Abfragen benötigten Spalten:

```text
source
device_id
received_at
temperature_c
humidity_pct
pressure_hpa
raw_s3_bucket
raw_s3_key
```

Ein zusätzlicher `processed` Bucket ist vorerst nicht geplant, weil die Messwerte bereits strukturiert und nah am finalen Tabellenmodell ankommen. Fehlerhafte oder unerwartete Payloads können später optional in einen `quarantine`-Prefix oder separaten Quarantine-Bucket geschrieben werden.

OpenWeather liefert ein größeres JSON als der Sensor. Das vollständige OpenWeather-JSON gehört in die Raw-Ablage. Für RDS werden daraus nur die normalisierten Felder `temperature_c`, `humidity_pct` und `pressure_hpa` plus Metadaten übernommen.

### RDS-Zugriff und Security

Die RDS-Instanz ist nicht öffentlich erreichbar. Der Zugriff auf PostgreSQL-Port `5432` wird über Security Groups auf die Lambda-Security-Group beschränkt. API Gateway hat keinen direkten Zugriff auf RDS; Requests laufen über die Lambda.

Der aktuelle Header-Token schützt sowohl den Schreibpfad `/sensor-readings` als auch den Lese-/Smoke-Test-Pfad `/latest-readings`. Der Token ist ein projektspezifisches Shared Secret und kein AWS-Zugangsschlüssel.

Für die Dev-Umgebung liegen Datenbankpasswort und Collector-Token aktuell über Terraform-Variablen bzw. Lambda-Environment-Variablen vor. Später können dafür AWS Secrets Manager oder SSM Parameter Store ergänzt werden. RDS Proxy ist ebenfalls mögliche Future Work, falls viele kurzlebige Lambda-Datenbankverbindungen relevant werden.

Für den aktuellen Dev-/Portfolio-Stand ist der Zugriff bewusst eingeschränkt: RDS ist privat, Grafana hat keine öffentliche Inbound-Regel, GitHub Actions nutzt OIDC statt langfristiger AWS Access Keys und der API-Schreibpfad ist token-geschützt. Das ist eine solide Dev-Basis, aber keine vollständige Produktionshärtung. Vor einem dauerhaft öffentlichen Portfolio-Betrieb sollten zusätzlich API Gateway Throttling, Lambda Reserved Concurrency und ein AWS Budget Alert ergänzt werden.

## Grafana

Grafana läuft in AWS auf einer EC2-Instanz als Docker-Container.
Der Zugriff erfolgt nicht öffentlich, sondern per SSM-Port-Forwarding.
Die RDS-Security-Group erlaubt PostgreSQL-Zugriff nur von Lambda und Grafana.
Das bestehende Dashboard nutzt die Datasource-UID `wetter-postgres` und funktioniert lokal sowie in der Cloud.

Das Cloud-Grafana-Image wird aus dem Repository gebaut und nach Amazon ECR gepusht. Lokal geht das weiterhin per Skript:

```bash
export AWS_PROFILE=iot-dev
./scripts/cloud/build-push-grafana-image.sh
```

Im normalen Cloud-Flow übernimmt GitHub Actions diesen Schritt. Der Workflow `deploy-grafana-image.yml` übernimmt per GitHub OIDC eine AWS-Rolle, baut das Grafana-Image, pusht es nach ECR und startet die Grafana-EC2 per SSM neu. Dadurch müssen keine langfristigen AWS Access Keys in GitHub Secrets gespeichert werden.

Der Grafana-Neustart kann lokal ebenfalls per SSM ausgelöst werden:

```bash
export AWS_PROFILE=iot-dev
./scripts/cloud/restart-grafana-from-ecr.sh
```

Der Zugriff auf Grafana erfolgt über einen lokalen SSM-Tunnel:

```bash
export AWS_PROFILE=iot-dev
./scripts/cloud/open-grafana-tunnel.sh
```

Standardmäßig öffnet das Skript Grafana lokal unter:

```text
http://localhost:3001
```

Das Dashboard wird im Grafana-Image provisioniert. Die Cloud-Datasource wird auf der EC2 über die Terraform-User-Data erzeugt, weil Host, Datenbankname und Passwort umgebungsspezifisch sind.

## Sicherheit, Secrets und öffentlicher Portfolio-Betrieb

Das Repository kann später öffentlich gemacht werden, solange keine echten Secrets oder lokalen State-Dateien enthalten sind. Der Cloud-Endpunkt darf im README sichtbar sein; der Schutz hängt am geheimen `X-Collector-Token` und an zusätzlichen Limits auf AWS-Seite.

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

Vor dem Veröffentlichen sollten diese Punkte geprüft werden:

```bash
git status --ignored
git ls-files | grep -E '(\.env|tfstate|tfvars|secrets\.h)$' || true
```

GitHub Secret Scanning und Push Protection sollten im Repository aktiviert bleiben. GitHub Actions verwendet für AWS bereits OIDC und keine dauerhaft gespeicherten AWS-Zugangsschlüssel.

Der Terraform-State liegt aktuell noch lokal und kann sensible Werte enthalten. Für einen robusteren öffentlichen Portfolio-Betrieb sollte der State in ein separates, nicht öffentliches S3-Backend mit Verschlüsselung, Versionierung und State Locking verschoben werden. Dieses Backend gehört zur Bootstrap-Infrastruktur und sollte getrennt von der normalen Dev-Umgebung verwaltet werden.

Geplantes Zielbild:

```text
separater Terraform-State-Bucket
  → Versioning aktiviert
  → Server-Side Encryption aktiviert
  → Public Access Block aktiviert
  → State Locking aktiviert
  → Zugriff nur für eigenen AWS-Admin/User und GitHub-OIDC-Role, falls Terraform später per CI läuft
```

Vor dem öffentlichen Bewerbungs-/Portfolio-Einsatz sollten außerdem API Gateway Throttling, Lambda Reserved Concurrency und ein AWS Budget Alert ergänzt werden, damit ein bekannter API-Endpunkt nicht beliebig Kosten verursachen kann.

### Kosten- und Destroy-Hinweis für AWS-Dev

API Gateway, Lambda und S3 verursachen bei diesem kleinen Dev-Setup überwiegend nutzungsabhängige bzw. sehr geringe Kosten. RDS und EC2 sind dagegen dauerhaft laufende Ressourcen und verursachen auch ohne aktive Abfragen Kosten, solange sie laufen.

Für kurze Arbeitspausen kann es sinnvoll sein, die Dev-Umgebung stehen zu lassen, damit RDS-Daten, Grafana und Dashboard-Zustand erhalten bleiben. Für längere Pausen ist `terraform destroy` günstiger. Ein späterer Neuaufbau aus S3 Raw-Daten ist möglich, solange der Raw Bucket nicht gelöscht wurde und ein Rebuild-Skript vorhanden ist. Aktuell löscht `terraform destroy` jedoch auch den von Terraform verwalteten S3 Raw Bucket; Rohdaten sollten daher vorher gesichert oder der Bucket bewusst aus dem Destroy-Pfad herausgenommen werden, wenn sie erhalten bleiben sollen.

Vor längeren Pausen kann die Dev-Umgebung zerstört werden:

```bash
cd infra/dev
export AWS_PROFILE=iot-dev
terraform plan -destroy
terraform destroy
```

Achtung: `terraform destroy` entfernt alle von dieser Terraform-Konfiguration verwalteten Ressourcen. Dazu gehören aktuell auch API Gateway, Lambda, RDS, Grafana-EC2 und der S3 Raw Bucket. Raw-Daten im S3 Bucket gehen dabei verloren, sofern sie vorher nicht gesichert wurden.


## Future Work

Mögliche spätere Erweiterungen:

* AWS IoT Core
* MQTT statt HTTP
* Device-Zertifikate
* vollständig automatisiertes AWS-Deployment mit Terraform
* API Gateway Throttling und Lambda Reserved Concurrency
* AWS Budget Alert für die Dev-Umgebung
* Remote Terraform State Backend in S3 mit State Locking
* optionaler späterer Wechsel von EC2 zu ECS/Fargate oder ALB/Domain
* AWS Secrets Manager oder SSM Parameter Store für Secrets
* RDS Proxy für robustere Lambda/RDS-Verbindungen
* Rebuild-Skript, das normalisierte RDS-Daten bei Bedarf aus S3 Raw-Daten wiederherstellt
