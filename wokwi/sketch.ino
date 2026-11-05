/*
  Chef Manos Libres — cocina inteligente simulada (ESP32 en Wokwi)

  Publica cada 2 s:   chefmanoslibres/grupo1/estado  (temperatura, humedad, fogón, paso, extractor...)
  Publica al ocurrir:  chefmanoslibres/grupo1/evento  (siguiente, atras, timer_fin, alerta_temp, conectado)
  Escucha:             chefmanoslibres/grupo1/cmd     (paso/total/texto/receta, timer, extractor,
                                                       extractor_auto, umbral, buzzer, fin)

  Pines: LCD I2C SDA 21 / SCL 22 · DHT22 15 · Perilla 34 · SIGUIENTE 26 · ATRÁS 27
         Buzzer 18 · LED verde 19 · LED rojo 23 · Servo extractor 13
*/
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>
#include <ESP32Servo.h>

// ---------------------------------------------------------------- configuración
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASS = "";
const char* BROKER    = "broker.hivemq.com";
const int   PUERTO    = 1883;

// Debe ser IGUAL al tópico de la app (config.py)
#define TOPICO_BASE "chefmanoslibres/grupo1"
const char* T_ESTADO = TOPICO_BASE "/estado";
const char* T_EVENTO = TOPICO_BASE "/evento";
const char* T_CMD    = TOPICO_BASE "/cmd";

#define PIN_DHT        15
#define PIN_PERILLA    34
#define PIN_SIGUIENTE  26
#define PIN_ATRAS      27
#define PIN_BUZZER     18
#define PIN_LED_VERDE  19
#define PIN_LED_ROJO   23
#define PIN_SERVO      13

// ---------------------------------------------------------------- objetos
LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(PIN_DHT, DHT22);
Servo extractor;
ESP32PWM buzzer;
WiFiClient wifi;
PubSubClient mqtt(wifi);

// ---------------------------------------------------------------- estado
String receta = "";
String textoPaso = "Chef Manos Libres";
int paso = 0, total = 0;
bool recetaTerminada = false;

float temperatura = NAN, humedad = NAN;
int fogon = 0;
float umbral = 45.0;
bool alerta = false;
unsigned long ultimoAvisoAlerta = 0;

bool extractorAuto = true;
bool extractorAbierto = false;
int anguloServo = -1;

bool timerActivo = false;
unsigned long timerFinMs = 0;
unsigned long ledRojoHastaMs = 0;

unsigned long ultimoEstado = 0, ultimoScroll = 0, ultimoIntento = 0;
int desplazamiento = 0;
String lcdLinea1 = "", lcdLinea2 = "";

// ---------------------------------------------------------------- buzzer sin bloquear
struct Nota { int frecuencia; int ms; };
const Nota SON_OK[]     = {{2000, 70}};
const Nota SON_BOTON[]  = {{1500, 60}};
const Nota SON_PRUEBA[] = {{1000, 180}, {0, 60}, {1500, 180}, {0, 60}, {2000, 250}};
const Nota SON_TIMER[]  = {{1800, 220}, {0, 120}, {1800, 220}, {0, 120}, {1800, 220}, {0, 120},
                           {1800, 220}, {0, 120}, {2400, 500}};
const Nota SON_ALERTA[] = {{2600, 160}, {0, 90}, {2600, 160}, {0, 90}, {2600, 160}, {0, 90}, {2600, 400}};
const Nota SON_FIN[]    = {{523, 160}, {659, 160}, {784, 160}, {1047, 400}};

const Nota* melodia = nullptr;
int largoMelodia = 0, notaActual = 0;
unsigned long finNotaMs = 0;

#define SONAR(arr) sonar(arr, sizeof(arr) / sizeof(Nota))

void silencio() { buzzer.write(0); }

void sonar(const Nota* m, int largo) {
  melodia = m; largoMelodia = largo; notaActual = 0;
  if (m[0].frecuencia > 0) buzzer.writeTone(m[0].frecuencia); else silencio();
  finNotaMs = millis() + m[0].ms;
}

void actualizarBuzzer() {
  if (!melodia || millis() < finNotaMs) return;
  notaActual++;
  if (notaActual >= largoMelodia) { melodia = nullptr; silencio(); return; }
  const Nota& n = melodia[notaActual];
  if (n.frecuencia > 0) buzzer.writeTone(n.frecuencia); else silencio();
  finNotaMs = millis() + n.ms;
}

// ---------------------------------------------------------------- utilidades
// El LCD no muestra tildes ni eñes: se reemplazan por la letra simple.
String sinTildes(const String& s) {
  String r = "";
  for (unsigned int i = 0; i < s.length(); i++) {
    uint8_t c = (uint8_t)s[i];
    if (c == 0xC3 && i + 1 < s.length()) {
      uint8_t d = (uint8_t)s[++i];
      switch (d) {
        case 0xA1: r += 'a'; break; case 0x81: r += 'A'; break;
        case 0xA9: r += 'e'; break; case 0x89: r += 'E'; break;
        case 0xAD: r += 'i'; break; case 0x8D: r += 'I'; break;
        case 0xB3: r += 'o'; break; case 0x93: r += 'O'; break;
        case 0xBA: r += 'u'; break; case 0x9A: r += 'U'; break;
        case 0xBC: r += 'u'; break; case 0x9C: r += 'U'; break;
        case 0xB1: r += 'n'; break; case 0x91: r += 'N'; break;
        default: break;
      }
    } else if (c == 0xC2 && i + 1 < s.length()) {
      i++;                       // ¿ ¡ ° : se omiten
    } else if (c < 0x80) {
      r += (char)c;
    }
  }
  return r;
}

String ajustar16(String s) {
  if (s.length() > 16) s = s.substring(0, 16);
  while (s.length() < 16) s += ' ';
  return s;
}

void publicarEvento(const char* tipo) {
  JsonDocument doc;
  doc["tipo"] = tipo;
  if (strcmp(tipo, "alerta_temp") == 0 && !isnan(temperatura)) doc["temperatura"] = round(temperatura * 10) / 10.0;
  char buf[128];
  serializeJson(doc, buf);
  mqtt.publish(T_EVENTO, buf);
  Serial.printf("evento -> %s\n", buf);
}

void publicarEstado() {
  JsonDocument doc;
  if (!isnan(temperatura)) doc["temperatura"] = round(temperatura * 10) / 10.0;
  if (!isnan(humedad)) doc["humedad"] = round(humedad * 10) / 10.0;
  doc["fogon"] = fogon;
  doc["receta"] = receta;
  doc["paso"] = paso;
  doc["total"] = total;
  doc["extractor"] = extractorAbierto;
  doc["extractor_auto"] = extractorAuto;
  doc["alerta_temp"] = alerta;
  doc["umbral"] = umbral;
  long restante = 0;
  if (timerActivo) restante = (long)(timerFinMs - millis()) / 1000 + 1;
  doc["timer_restante"] = restante < 0 ? 0 : restante;
  char buf[384];
  serializeJson(doc, buf);
  mqtt.publish(T_ESTADO, buf);
}

// ---------------------------------------------------------------- actuadores
void moverExtractor() {
  int angulo = extractorAbierto ? 90 : 0;
  if (angulo != anguloServo) {
    extractor.write(angulo);
    anguloServo = angulo;
  }
}

void actualizarLeds() {
  bool rojo = alerta || millis() < ledRojoHastaMs;
  digitalWrite(PIN_LED_ROJO, rojo ? HIGH : LOW);
  digitalWrite(PIN_LED_VERDE, (mqtt.connected() && !alerta) ? HIGH : LOW);
}

void actualizarLcd() {
  String l1;
  if (recetaTerminada) l1 = "Buen provecho!";
  else if (total > 0 && paso > 0) l1 = "P" + String(paso) + "/" + String(total) + " " + sinTildes(textoPaso);
  else l1 = sinTildes(textoPaso);

  if (l1.length() > 16) {                 // texto largo: se desplaza cada 400 ms
    String vuelta = l1 + "   ";
    int n = vuelta.length();
    int ini = desplazamiento % n;
    String doble = vuelta + vuelta;
    l1 = doble.substring(ini, ini + 16);
  }

  char l2[17];
  if (!mqtt.connected()) {
    snprintf(l2, sizeof(l2), "Sin conexion...");
  } else if (alerta) {
    snprintf(l2, sizeof(l2), "ALERTA %4.1fC", temperatura);
  } else if (timerActivo) {
    long r = (long)(timerFinMs - millis()) / 1000 + 1;
    if (r < 0) r = 0;
    snprintf(l2, sizeof(l2), "Timer %02ld:%02ld", r / 60, r % 60);
  } else if (isnan(temperatura)) {
    snprintf(l2, sizeof(l2), "Fogon %3d%%", fogon);
  } else {
    snprintf(l2, sizeof(l2), "T:%4.1fC F:%3d%%", temperatura, fogon);
  }

  String a = ajustar16(l1), b = ajustar16(String(l2));
  if (a != lcdLinea1) { lcd.setCursor(0, 0); lcd.print(a); lcdLinea1 = a; }
  if (b != lcdLinea2) { lcd.setCursor(0, 1); lcd.print(b); lcdLinea2 = b; }
}

// ---------------------------------------------------------------- comandos desde la app
void alRecibir(char* topico, byte* payload, unsigned int largo) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, payload, largo);
  if (err) { Serial.printf("JSON invalido: %s\n", err.c_str()); return; }
  Serial.printf("cmd <- %.*s\n", (int)largo, (char*)payload);

  if (!doc["texto"].isNull()) {
    textoPaso = doc["texto"].as<String>();
    if (!doc["paso"].isNull()) paso = doc["paso"].as<int>();
    if (!doc["total"].isNull()) total = doc["total"].as<int>();
    if (!doc["receta"].isNull()) receta = doc["receta"].as<String>();
    recetaTerminada = false;
    desplazamiento = 0;
    SONAR(SON_OK);                         // pitido de confirmación
  }
  if (!doc["timer"].isNull()) {
    long s = doc["timer"].as<long>();
    if (s > 0) { timerActivo = true; timerFinMs = millis() + (unsigned long)s * 1000UL; SONAR(SON_OK); }
    else { timerActivo = false; }
  }
  if (!doc["extractor_auto"].isNull()) extractorAuto = doc["extractor_auto"].as<bool>();
  if (!doc["extractor"].isNull()) {         // control manual desde la app
    extractorAuto = false;
    extractorAbierto = doc["extractor"].as<bool>();
  }
  if (!doc["umbral"].isNull()) umbral = doc["umbral"].as<float>();
  if (doc["buzzer"].as<bool>()) SONAR(SON_PRUEBA);
  if (doc["fin"].as<bool>()) {
    recetaTerminada = true;
    timerActivo = false;
    SONAR(SON_FIN);
  }
  moverExtractor();
  actualizarLcd();
  publicarEstado();                          // la app ve el cambio de inmediato
}

// ---------------------------------------------------------------- conexión
void conectarWifi() {
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print("Conectando WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASS, 6);
  int i = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    lcd.setCursor(i % 16, 1); lcd.print(".");
    i++;
  }
  Serial.println("WiFi conectado: " + WiFi.localIP().toString());
}

void conectarMqtt() {
  if (mqtt.connected() || millis() - ultimoIntento < 2000) return;   // reintenta cada 2 s
  ultimoIntento = millis();
  if (WiFi.status() != WL_CONNECTED) { WiFi.reconnect(); return; }
  String id = "chefml-esp32-" + String((uint32_t)ESP.getEfuseMac(), HEX) + String(random(0xffff), HEX);
  Serial.print("Conectando a MQTT... ");
  if (mqtt.connect(id.c_str())) {
    Serial.println("listo");
    mqtt.subscribe(T_CMD);
    publicarEvento("conectado");
    publicarEstado();
    SONAR(SON_OK);
  } else {
    Serial.printf("fallo, rc=%d\n", mqtt.state());
  }
}

// ---------------------------------------------------------------- botones con antirrebote de 50 ms
struct Boton {
  int pin; const char* evento;
  int estable; int lectura; unsigned long cambio;
};
Boton botones[] = {
  {PIN_SIGUIENTE, "siguiente", HIGH, HIGH, 0},
  {PIN_ATRAS, "atras", HIGH, HIGH, 0},
};

void leerBotones() {
  for (Boton& b : botones) {
    int l = digitalRead(b.pin);
    if (l != b.lectura) { b.lectura = l; b.cambio = millis(); }
    if (millis() - b.cambio > 50 && l != b.estable) {
      b.estable = l;
      if (l == LOW) {                        // se presionó (INPUT_PULLUP)
        SONAR(SON_BOTON);
        if (mqtt.connected()) publicarEvento(b.evento);
      }
    }
  }
}

// ---------------------------------------------------------------- sensores
void leerSensores() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t)) temperatura = t;
  if (!isnan(h)) humedad = h;
  fogon = map(analogRead(PIN_PERILLA), 0, 4095, 0, 100);

  bool nuevaAlerta = !isnan(temperatura) && temperatura > umbral;
  if (nuevaAlerta && !alerta) {
    publicarEvento("alerta_temp");
    SONAR(SON_ALERTA);
    ultimoAvisoAlerta = millis();
  } else if (nuevaAlerta && millis() - ultimoAvisoAlerta > 15000) {
    SONAR(SON_ALERTA);                       // recuerda la alerta cada 15 s
    ultimoAvisoAlerta = millis();
  }
  alerta = nuevaAlerta;

  if (extractorAuto) extractorAbierto = alerta || fogon > 70;
  moverExtractor();
}

// ---------------------------------------------------------------- setup / loop
void setup() {
  Serial.begin(115200);
  pinMode(PIN_SIGUIENTE, INPUT_PULLUP);
  pinMode(PIN_ATRAS, INPUT_PULLUP);
  pinMode(PIN_LED_VERDE, OUTPUT);
  pinMode(PIN_LED_ROJO, OUTPUT);

  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  extractor.setPeriodHertz(50);
  extractor.attach(PIN_SERVO, 500, 2400);
  moverExtractor();
  buzzer.attachPin(PIN_BUZZER, 1000, 10);
  silencio();

  lcd.init();
  lcd.backlight();
  dht.begin();
  randomSeed(micros());

  conectarWifi();
  mqtt.setServer(BROKER, PUERTO);
  mqtt.setBufferSize(1024);                  // los pasos de la receta pueden ser largos
  mqtt.setCallback(alRecibir);
  lcd.clear();
}

void loop() {
  conectarMqtt();
  mqtt.loop();
  leerBotones();
  actualizarBuzzer();

  // temporizador con millis(), sin bloquear
  if (timerActivo && (long)(millis() - timerFinMs) >= 0) {
    timerActivo = false;
    ledRojoHastaMs = millis() + 5000;
    SONAR(SON_TIMER);
    if (mqtt.connected()) publicarEvento("timer_fin");
  }

  unsigned long ahora = millis();
  if (ahora - ultimoEstado >= 2000) {
    ultimoEstado = ahora;
    leerSensores();
    if (mqtt.connected()) publicarEstado();
  }
  if (ahora - ultimoScroll >= 400) {
    ultimoScroll = ahora;
    desplazamiento++;
    actualizarLcd();
  }
  actualizarLeds();
}
