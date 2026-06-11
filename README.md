# IoT-Wetterdaten-Pipeline

Lokales Portfolio-Projekt für eine kleine IoT-Wetterstation.

Ein ESP32-C6-Zero mit BME280-Sensor misst Temperatur, Luftfeuchtigkeit und Luftdruck und sendet die Messwerte per HTTP an einen lokalen FastAPI-Collector. Der Collector speichert die Rohdaten in einem lokalen S3-kompatiblen Speicher über LocalStack und legt die validierten Messwerte zusätzlich in PostgreSQL ab. Grafana visualisiert die Messwerte aus PostgreSQL.

## Aktueller Datenfluss

```text
ESP32-C6-Zero + BME280
        ↓ HTTP POST
FastAPI Collector
        ├── Raw JSON → LocalStack S3
        └── validierte Messwerte → PostgreSQL
                                      ↓
                                   Grafana
```

## Aktuelle Ordnerstruktur

scripts/
├── send-test-reading.sh          # sendet künstliche Sensordaten
├── send-fallback-reading.sh      # sendet künstliche Fallback-Daten
├── fetch-openweather-reading.py  # ruft echte OpenWeather-Daten ab
├── show-latest-readings.sh       # zeigt letzte PostgreSQL-Zeilen
└── list-raw-objects.sh           # zeigt Raw-Objekte in LocalStack S3

## Aktueller Projektstand

Bereits umgesetzt:

* ESP32 sendet Messwerte per HTTP POST.
* FastAPI nimmt Messwerte entgegen.
* Der Collector akzeptiert `/readings` und `/sensor-readings`.
* Messwerte werden validiert.
* Rohdaten werden in LocalStack S3 gespeichert.
* Validierte Messwerte werden in PostgreSQL gespeichert.
* Grafana wird lokal per Docker gestartet.
* PostgreSQL-Datenquelle und Dashboard werden automatisch in Grafana provisioniert.

Noch nicht umgesetzt:

* OpenWeather-Fallback
* GitHub Actions
* Terraform
* AWS-Deployment
* Amazon RDS
* Deployment des Dashboards auf EC2

## Hardware

Board:

```text
Waveshare ESP32-C6-Zero / ESP32-C6-Mini
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
temperature_c: -50 bis 80
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
* LocalStack
* optional: AWS CLI für lokale S3-Prüfungen

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
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=eu-central-1

LOCALSTACK_ENDPOINT=http://localhost:4566
RAW_BUCKET=weather-raw

COLLECTOR_HOST=0.0.0.0
COLLECTOR_PORT=8088

POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=weather
POSTGRES_USER=weather
POSTGRES_PASSWORD=weather
```

Die Datei `.env` wird nicht committed.

Die LocalStack-Zugangsdaten `test/test` sind lokale Dummy-Werte und gehören nicht zu einem echten AWS-Account.

## Lokalen Stack starten

### 1. LocalStack starten

In einem eigenen Terminal:

```bash
export LOCALSTACK_AUTH_TOKEN=<dein-token>
localstack start
```

LocalStack läuft lokal unter:

```text
http://localhost:4566
```

### 2. PostgreSQL und Grafana starten

In einem zweiten Terminal im Projektordner:

```bash
docker compose up -d postgres grafana
```

PostgreSQL ist auf dem Host unter Port `5433` erreichbar, weil Port `5432` lokal bereits belegt sein kann.

Im Docker-Netzwerk verwendet Grafana aber den internen PostgreSQL-Port:

```text
wetter-postgres:5432
```

### 3. FastAPI Collector starten

In einem dritten Terminal:

```bash
set -a
source .env
set +a

uvicorn src.collector.main:app --host 0.0.0.0 --port 8088 --reload
```

Health Check:

```bash
curl http://localhost:8088/health
```

Erwartete Antwort:

```json
{"status":"ok"}
```

## Testdaten senden

Ohne echten Sensor:

```bash
./scripts/send-test-reading.sh
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
./scripts/show-latest-readings.sh
```

Oder direkt:

```bash
docker exec -it wetter-postgres psql -U weather -d weather -c \
"SELECT id, device_id, received_at, temperature_c, humidity_pct, pressure_hpa
 FROM weather_readings
 ORDER BY id DESC
 LIMIT 10;"
```

## LocalStack S3 prüfen

Wenn AWS CLI installiert ist:

```bash
source .env
./scripts/list-raw-objects.sh
```

Oder direkt:

```bash
AWS_ACCESS_KEY_ID=test \
AWS_SECRET_ACCESS_KEY=test \
AWS_DEFAULT_REGION=eu-central-1 \
aws --endpoint-url=http://localhost:4566 \
  s3 ls s3://weather-raw --recursive
```

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

Wenn keine Daten angezeigt werden:

1. Prüfen, ob PostgreSQL Daten enthält.
2. Grafana-Zeitfenster auf `Last 6 hours` oder `Last 24 hours` setzen.
3. In Grafana Explore die Datenquelle `Wetter PostgreSQL` testen.

Beispielquery:

```sql
SELECT
  received_at AS "time",
  temperature_c AS "Temperatur °C"
FROM weather_readings
ORDER BY received_at;
```

## Sensor-URL

Der ESP32 darf nicht an `localhost` senden, sondern an die LAN-IP des Rechners, auf dem FastAPI läuft.

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

| Komponente        | Zweck                                                       |
| ----------------- | ----------------------------------------------------------- |
| ESP32-C6 + BME280 | echte lokale Sensordaten                                    |
| FastAPI           | einfacher HTTP-Collector                                    |
| LocalStack S3     | lokales Raw-Datenarchiv                                     |
| PostgreSQL        | strukturierte Messwerte für Abfragen                        |
| Grafana           | Visualisierung der Messwerte                                |
| Docker Compose    | reproduzierbarer lokaler Betrieb von PostgreSQL und Grafana |

## Nächste geplante Schritte

1. README und lokalen Ablauf stabilisieren.
2. Datenmodell um eine Spalte `source` erweitern.
3. Künstliche Fallback-Werte als alternative Datenquelle testen.
4. Danach echte OpenWeather-Anbindung ergänzen.
5. Erst danach GitHub Actions und Terraform vorbereiten.
6. Später: PostgreSQL lokal durch Amazon RDS for PostgreSQL ersetzen.
