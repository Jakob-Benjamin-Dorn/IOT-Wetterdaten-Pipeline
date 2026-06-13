#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>

#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

#include "secrets.h"

// ESP32-C6-Zero / BME280 I2C Pins
#define I2C_SDA 4
#define I2C_SCL 5

// BME280 I2C-Adressen
#define BME280_ADDRESS_PRIMARY 0x77
#define BME280_ADDRESS_SECONDARY 0x76

// Sendeintervall
const unsigned long SEND_INTERVAL_MS = 60000;

// Timeouts / Recovery
const unsigned long WIFI_CONNECT_TIMEOUT_MS = 20000;
const unsigned long HTTP_TIMEOUT_MS = 10000;
const int MAX_CONSECUTIVE_SEND_FAILURES = 5;

Adafruit_BME280 bme;

unsigned long lastSendAt = 0;
int consecutiveSendFailures = 0;


const char* getCollectorUrl() {
  if (USE_CLOUD) {
    return CLOUD_COLLECTOR_URL;
  }

  return LOCAL_COLLECTOR_URL;
}


const char* getCollectorToken() {
  if (USE_CLOUD) {
    return CLOUD_COLLECTOR_TOKEN;
  }

  return "";
}


void printStartupConfig() {
  Serial.println("--- Konfiguration ---");
  Serial.print("Modus: ");
  Serial.println(USE_CLOUD ? "CLOUD" : "LOCAL");

  Serial.print("Device ID: ");
  Serial.println(DEVICE_ID);

  Serial.print("Collector URL: ");
  Serial.println(getCollectorUrl());

  Serial.print("Sendeintervall ms: ");
  Serial.println(SEND_INTERVAL_MS);

  Serial.print("Max. aufeinanderfolgende Sendefehler: ");
  Serial.println(MAX_CONSECUTIVE_SEND_FAILURES);
}


void connectToWifi() {
  Serial.print("Verbinde mit WLAN: ");
  Serial.println(WIFI_SSID);

  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startAttempt = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < WIFI_CONNECT_TIMEOUT_MS) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WLAN-Verbindung fehlgeschlagen. Neustart in 5 Sekunden...");
    delay(5000);
    ESP.restart();
  }

  Serial.println("WLAN verbunden.");
  Serial.print("IP-Adresse: ");
  Serial.println(WiFi.localIP());
}


void setupBme280() {
  Serial.println("--- BME280 Initialisierung ---");

  Wire.begin(I2C_SDA, I2C_SCL);

  if (!bme.begin(BME280_ADDRESS_PRIMARY, &Wire)) {
    Serial.println("Sensor nicht gefunden auf 0x77, teste 0x76...");

    if (!bme.begin(BME280_ADDRESS_SECONDARY, &Wire)) {
      Serial.println("BME280 nicht gefunden.");
      Serial.println("Bitte Verkabelung prüfen: VCC, GND, SDA=GPIO4, SCL=GPIO5.");

      while (true) {
        delay(1000);
      }
    }
  }

  Serial.println("BME280 erfolgreich verbunden.");
}


String buildPayload(float temperatureC, float humidityPct, float pressureHpa) {
  String payload = "{";
  payload += "\"device_id\":\"";
  payload += DEVICE_ID;
  payload += "\",";
  payload += "\"temperature_c\":";
  payload += String(temperatureC, 2);
  payload += ",";
  payload += "\"humidity_pct\":";
  payload += String(humidityPct, 2);
  payload += ",";
  payload += "\"pressure_hpa\":";
  payload += String(pressureHpa, 2);
  payload += "}";

  return payload;
}


bool isHttpsUrl(const char* url) {
  String value = String(url);
  value.toLowerCase();

  return value.startsWith("https://");
}


void handleSendResult(bool success) {
  if (success) {
    if (consecutiveSendFailures > 0) {
      Serial.println("Senden wieder erfolgreich. Fehlerzähler wird zurückgesetzt.");
    }

    consecutiveSendFailures = 0;
    return;
  }

  consecutiveSendFailures++;

  Serial.print("Sendeversuch fehlgeschlagen. Fehler in Folge: ");
  Serial.println(consecutiveSendFailures);

  if (consecutiveSendFailures >= MAX_CONSECUTIVE_SEND_FAILURES) {
    Serial.println("Zu viele aufeinanderfolgende Sendefehler. Neustart in 3 Sekunden...");
    delay(3000);
    ESP.restart();
  }
}


bool executePost(HTTPClient& http, const String& payload, const char* collectorToken) {
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.addHeader("Content-Type", "application/json");

  if (String(collectorToken).length() > 0) {
    http.addHeader("X-Collector-Token", collectorToken);
  }

  int httpCode = http.POST(payload);

  Serial.print("HTTP Status: ");
  Serial.println(httpCode);

  String response = http.getString();

  Serial.print("Response: ");
  Serial.println(response);

  return httpCode >= 200 && httpCode < 300;
}


void sendReading() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WLAN getrennt. Verbinde neu...");
    connectToWifi();
  }

  float temperatureC = bme.readTemperature();
  float humidityPct = bme.readHumidity();
  float pressureHpa = bme.readPressure() / 100.0F;

  if (isnan(temperatureC) || isnan(humidityPct) || isnan(pressureHpa)) {
    Serial.println("Ungültige Sensordaten gelesen. Sendevorgang übersprungen.");
    return;
  }

  Serial.println("--- Messwerte ---");
  Serial.print("Temperatur: ");
  Serial.print(temperatureC);
  Serial.println(" °C");

  Serial.print("Luftfeuchtigkeit: ");
  Serial.print(humidityPct);
  Serial.println(" %");

  Serial.print("Luftdruck: ");
  Serial.print(pressureHpa);
  Serial.println(" hPa");

  String payload = buildPayload(temperatureC, humidityPct, pressureHpa);

  const char* collectorUrl = getCollectorUrl();
  const char* collectorToken = getCollectorToken();

  Serial.println("--- HTTP POST ---");
  Serial.print("URL: ");
  Serial.println(collectorUrl);
  Serial.print("Payload: ");
  Serial.println(payload);

  HTTPClient http;
  bool success = false;

  if (isHttpsUrl(collectorUrl)) {
    WiFiClientSecure secureClient;

    // Für den MVP pragmatisch.
    // Später besser: echtes Root-CA-Zertifikat setzen statt setInsecure().
    secureClient.setInsecure();

    if (!http.begin(secureClient, collectorUrl)) {
      Serial.println("HTTPS-Verbindung konnte nicht initialisiert werden.");
      handleSendResult(false);
      return;
    }

    success = executePost(http, payload, collectorToken);
    http.end();
    handleSendResult(success);

    return;
  }

  WiFiClient client;

  if (!http.begin(client, collectorUrl)) {
    Serial.println("HTTP-Verbindung konnte nicht initialisiert werden.");
    handleSendResult(false);
    return;
  }

  success = executePost(http, payload, collectorToken);
  http.end();
  handleSendResult(success);
}


void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("ESP32-C6 Wetterstation startet...");

  printStartupConfig();
  setupBme280();
  connectToWifi();

  sendReading();
  lastSendAt = millis();
}


void loop() {
  unsigned long now = millis();

  if (now - lastSendAt >= SEND_INTERVAL_MS) {
    sendReading();
    lastSendAt = now;
  }
}
