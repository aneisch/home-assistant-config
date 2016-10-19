#include <ESP8266WiFi.h>
#include <PubSubClient.h>

const char *ssid =  "SSID";   // cannot be longer than 32 characters!
const char *pass =  "PASSCODE";   //
const char *mqtt_server = "MQTT_IP";
const int mqtt_port = MQTT_PORT;
const char* connection_id = "ESP8266Client3";
const char* client_name = "MQTT_USERNAME";
const char* client_password = "MQTT_PASSCODE";
const char* topic = "bed-toggle/state";
char somebigthing[100];

const int buttonPin = D3;
const int ledPin = BUILTIN_LED;

WiFiClient espClient;
PubSubClient client(espClient);

// the current state of the LED and button
int ledState = LOW;
int buttonState = LOW;

// the current and previous readings from the input pin
int thisButtonState = LOW;
int lastButtonState = LOW;

// time is measured in milliseconds and will quickly exceed limitations of an integer, so we use a long for these two
unsigned long lastDebounceTime = 0;  // the time the button state last switched
unsigned long debounceDelay = 50;    // the state must remain the same for this many millis to register the button press

void setup() {
  Serial.begin(9600);
  pinMode(buttonPin, INPUT);
  client.setServer(mqtt_server, mqtt_port); // MQTT!!!
}

void loop() {
  WiFi.begin(ssid, pass);
  client.connect(connection_id, client_name, client_password);
  // the buttonPin is read multiple times and the value must remain the same for debounceDelay millis to toggle the LED

  // read button state, HIGH when pressed, LOW when not
  thisButtonState = digitalRead(buttonPin);

  // if the current state does not match the previous state
  // the button was just pressed/released, or is transition noise
  if (thisButtonState != lastButtonState) {
    // reset the timer
    lastDebounceTime = millis();
  }

  // once delay millis have elapsed, if the state remains the same, register the press
  if ((millis() - lastDebounceTime) > debounceDelay) {

    // if the button state has changed
    if (thisButtonState != buttonState) {
      buttonState = thisButtonState;

      // only toggle the LED if the buttonState has switched from LOW to HIGH
      if (buttonState == HIGH) {
        ledState = !ledState;
        // toggle the LED
        if (ledState == HIGH) {
          SendOn();
        }
        else {
          SendOff();
        }
      }
    }
  }

  // persist for next loop iteration
  lastButtonState = thisButtonState;
}

void SendOn(){
  strcpy(somebigthing,  "{\"enabled\":\"true\"}");
  client.publish(topic, somebigthing);
}


void SendOff(){
  strcpy(somebigthing,  "{\"enabled\":\"false\"}");
  client.publish(topic, somebigthing);
}
