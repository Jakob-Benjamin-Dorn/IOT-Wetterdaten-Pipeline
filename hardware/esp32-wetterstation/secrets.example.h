#pragma once

// Kopiere diese Datei zu secrets.h und trage echte Werte ein.
// secrets.h NICHT committen.

#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASSWORD "your-wifi-password"

#define LOCAL_COLLECTOR_URL "http://YOUR_LOCAL_IP:8088/sensor-readings"
#define CLOUD_COLLECTOR_URL "https://sensor-domain-jakob.click/sensor-readings"

#define CLOUD_COLLECTOR_TOKEN "your-cloud-token"

#define DEVICE_ID "esp32-c6-window-01"

// false = lokal testen
// true  = Cloud senden
#define USE_CLOUD false

