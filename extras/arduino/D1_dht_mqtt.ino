#include <ESP8266WiFi.h>
#include <PubSubClient.h>


const char *ssid =  "SSID";   // cannot be longer than 32 characters!
const char *pass =  "PASSCODE";   //
const char *mqtt_server = "10.0.1.22";
const int mqtt_port = 1883;
const char* connection_id = "d1_mini_1";
const char* client_name = "MQTT_USERNAME";
const char* client_password = "MQTT_PASSWORD";
const char* topic = "sensor/dht_mini_1";
const int sleepSeconds = 300;

#include "DHT.h"

#define DHTPIN D4     // what pin we're connected to

// Uncomment whatever type you're using! 
//#define DHTTYPE DHT11   // DHT 11
#define DHTTYPE DHT22   // DHT 22  (AM2302)
//#define DHTTYPE DHT21   // DHT 21 (AM2301)


DHT dht(DHTPIN, DHTTYPE);
unsigned long previousMillis = 0;
const long interval = 10000;  
float tempF = 0; 
char somebigthing[100];
char humidity[6];
char headindex[6];


WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  WiFi.mode(WIFI_STA); //Stop wifi broadcast
  client.setServer(mqtt_server, mqtt_port); // MQTT!!!
  // Setup console
  Serial.begin(9600);
  delay(10);
  pinMode(D0, WAKEUP_PULLUP);

  dht.begin();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    //Serial.print("Connecting to ");
    //Serial.print(ssid);
    //Serial.println("...");
    WiFi.begin(ssid, pass);

    if (WiFi.waitForConnectResult() != WL_CONNECTED)
      return;
    Serial.println("WiFi connected");
  }

  if (WiFi.status() == WL_CONNECTED) {
    if (!client.connected()) {
      Serial.println("Connecting to MQTT server");
      if (client.connect(connection_id, client_name, client_password)) {
        Serial.println("Connected to MQTT server");
      } else {
        Serial.println("Could not connect to MQTT server");   
      }
    }

    if (client.connected())
      client.loop();
  }
  delay(5000);
  //ESP.deepSleep(sleepSeconds * 1000000);
  SendInfo();
}



void SendInfo(){
  unsigned long currentMillis = millis();
 
  if(currentMillis - previousMillis >= interval) {
    // save the last time you read the sensor 
    previousMillis = currentMillis;   
 
    float h = dht.readHumidity();
    float t = dht.readTemperature(true);

    if (isnan(h) || isnan(t)) {
      Serial.println("Failed to read from DHT sensor, trying again");
      //return; This will ensure that data is always sent
    }
    else {
      
    delay(2000);

    static char Fout[15];
    dtostrf(t,4, 2, Fout);
 
    float hif = dht.computeHeatIndex(t, h); //heat index
    static char index[15];
    dtostrf(hif,4, 2, index);
    
    //sprintf(humidity, "%d", (int)h);
    static char humidity[15];
    dtostrf(h,4, 2, humidity);
    
    strcpy(somebigthing,  "{\"temperature\":\"");
    strcat(somebigthing, Fout);
    strcat(somebigthing, "\",");
    strcat(somebigthing,  "\"humidity\":\"");
    strcat(somebigthing, humidity);
    strcat(somebigthing, "\",");
    strcat(somebigthing,  "\"heat_index\":\"");
    strcat(somebigthing, index);
    strcat(somebigthing, "\"}");
    
    //sprintf(tempFstring, "%d", (int)tempF);
    Serial.printf(somebigthing);
    client.publish(topic, somebigthing);
    }
  }
}
