#include <ESP8266WiFi.h>
#include <PubSubClient.h>

const char *ssid =  "SSID";   // cannot be longer than 32 characters!
const char *pass =  "PASSCODE";   //
const char *mqtt_server = "MQTT_IP";
const int mqtt_port = MQTT_PORT;
const char* connection_id = "ESP8266Client3";
const char* client_name = "MQTT_USERNAME";
const char* client_password = "MQTT_PASSCODE";
const char* backdoorTopic = "sensor/backdoor";
const char* frontdoorTopic = "sensor/frontdoor";
const char* backwindowTopic = "sensor/backwindow";
const char* frontwindowTopic = "sensor/frontwindow";
char somebigthing[100];

const int backdoor = D3;
const int frontdoor = D4;
const int backwindow = D6;
const int frontwindow = D7;

//Need 10k pullup resistors for others!!

int backdoorState = 0;
int lastbackdoorState = 0;

int frontdoorState = 0;
int lastfrontdoorState = 0;

int backwindowState = 0;
int lastbackwindowState = 0;

int frontwindowState = 0;
int lastfrontwindowState = 0;

WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  int backdoorState = 0;
  int frontdoorState = 0;
  int backwindowState = 0;
  int frontwindowState = 0;
  pinMode(backdoor, INPUT);
  pinMode(frontdoor, INPUT);
  pinMode(backwindow, INPUT);
  pinMode(frontwindow, INPUT);
  client.setServer(mqtt_server, mqtt_port); // MQTT!!!
}

void loop() {
  WiFi.begin(ssid, pass);
  client.connect(connection_id, client_name, client_password);

  backdoorState = digitalRead(backdoor);
  frontdoorState = digitalRead(frontdoor);
  backwindowState = digitalRead(backwindow);
  frontwindowState = digitalRead(frontwindow);
  

  if (backdoorState != lastbackdoorState) {
    if (backdoorState == HIGH) {
    Serial.println("Switch backdoor is on");
    SendBackdoorOn();
  }
  else {
    Serial.println("Switch backdoor is off");
    SendBackdoorOff();
  }

  }
  
  if (frontdoorState != lastfrontdoorState) {
    if (frontdoorState == HIGH) {
    SendFrontdoorOn();
  }
  else {
    SendFrontdoorOff();
  }
 }  

  if (frontwindowState != lastfrontwindowState) {
    if (frontwindowState == HIGH) {
    SendFrontwindowOn();
  }
  else {
    SendFrontwindowOff();
  }
 } 

  if (backwindowState != lastbackwindowState) {
    if (backwindowState == HIGH) {
    SendBackwindowOn();
  }
  else {
    SendBackwindowOff();
  }
 } 

lastfrontdoorState = frontdoorState;
lastbackdoorState = backdoorState;
lastfrontwindowState = frontwindowState;
lastbackwindowState = backwindowState;
}


void SendBackdoorOn(){
  strcpy(somebigthing,  "{\"opened\":\"true\"}");
  client.publish(backdoorTopic, somebigthing, true);
}
void SendBackdoorOff(){
  strcpy(somebigthing,  "{\"opened\":\"false\"}");
  client.publish(backdoorTopic, somebigthing, true); 
}
void SendFrontdoorOn(){
  strcpy(somebigthing,  "{\"opened\":\"true\"}");
  client.publish(frontdoorTopic, somebigthing, true);
}
void SendFrontdoorOff(){
  strcpy(somebigthing,  "{\"opened\":\"false\"}");
  client.publish(frontdoorTopic, somebigthing, true); 
}
void SendBackwindowOn(){
  strcpy(somebigthing,  "{\"opened\":\"true\"}");
  client.publish(backwindowTopic, somebigthing, true);
}
void SendBackwindowOff(){
  strcpy(somebigthing,  "{\"opened\":\"false\"}");
  client.publish(backwindowTopic, somebigthing, true); 
}
void SendFrontwindowOn(){
  strcpy(somebigthing,  "{\"opened\":\"true\"}");
  client.publish(frontwindowTopic, somebigthing, true);
}
void SendFrontwindowOff(){
  strcpy(somebigthing,  "{\"opened\":\"false\"}");
  client.publish(frontwindowTopic, somebigthing, true); 
}
