# IoT-Wetterdaten-Pipeline

[![CI](https://github.com/Jakob-Benjamin-Dorn/IOT-Wetterdaten-Pipeline/actions/workflows/tests.yml/badge.svg)](https://github.com/Jakob-Benjamin-Dorn/IOT-Wetterdaten-Pipeline/actions/workflows/tests.yml)

Lokales Portfolio-Projekt für eine kleine IoT-Wetterstation.

Ein ESP32-C6-Zero mit BME280-Sensor misst Temperatur, Luftfeuchtigkeit und Luftdruck und sendet die Messwerte per HTTP an einen FastAPI-Collector. Der Collector speichert die Rohdaten in einem S3-kompatiblen Raw-Archiv über LocalStack und legt die validierten Messwerte zusätzlich in PostgreSQL ab. Grafana visualisiert die Messwerte aus PostgreSQL.

Zusätzlich kann eine OpenWeather-basierte Fallback-Quelle genutzt werden, wenn längere Zeit keine aktuellen Sensordaten eintreffen.

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

## Aktuelle Ordnerstruktur

```text
src/collector/
├── main.py            # FastAPI-Adapter für den lokalen HTTP-Collector
├── lambda_handler.py  # vorbereiteter Lambda-Adapter für späteres API-Gateway/Lambda-Deployment
├── ingestion.py       # eigentliche Ingestion-/Speicherlogik
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

tests/
├── test_config.py
├── test_fallback.py
├── test_ingestion.py
├── test_lambda_handler.py
└── test_models.py
```

## Aktueller Projektstand

Bereits umgesetzt:

* ESP32 sendet Messwerte per HTTP POST.
* FastAPI nimmt Messwerte entgegen.
* Der Collector akzeptiert `/readings` und `/sensor-readings`.
* Messwerte werden validiert.
* Rohdaten werden in LocalStack S3 gespeichert.
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
* Ein Lambda-Adapter ist als Cloud-Readiness-Vorbereitung vorhanden, aber noch nicht deployed.

Noch nicht umgesetzt:

* Terraform
* AWS-Deployment
* Amazon RDS
* API Gateway / Lambda Deployment
* Deployment von Grafana auf ECS/EC2
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

Der Sensor sendet aktuell ungefähr alle 30 Sekunden. Für die spätere Demo ist ein Intervall von 60 Sekunden vorgesehen.

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

Langfristiges Ziel:

```text
Grafana auf ECS/EC2
→ PostgreSQL Datasource
→ Amazon RDS PostgreSQL
```

Grafana liest die neuesten Daten also aus RDS. Der Collector muss dafür nicht als dauerhaft laufender Container in AWS betrieben werden, wenn die Datenaufnahme über API Gateway + Lambda erfolgt.

## Infrastruktur-Kategorien

### Bootstrap-Infrastruktur

Diese Infrastruktur sollte möglichst stabil bleiben und nicht regelmäßig zerstört werden:

* Domain / Route 53 Hosted Zone
* TLS-Zertifikate
* GitHub OIDC Provider
* Terraform State Backend
* ECR Repository für spätere Grafana-Images
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

## Future Work

Mögliche spätere Erweiterungen:

* AWS IoT Core
* MQTT statt HTTP
* Device-Zertifikate
* IoT Rules
* vollständig automatisiertes AWS-Deployment mit Terraform
* Grafana-Deployment auf ECS/EC2
