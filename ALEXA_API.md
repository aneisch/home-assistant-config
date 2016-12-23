# Alexa API Setup

###Intents
Intents are the things we use to link our utterances and our custom slots.

### For example:

**Intent Schema**:
```
{
  "intents": [
      {
      "intent": "ActivateIntent",
      "slots":[
        {
        	"name" : "Group",
          "type" : "Groups"
        }
      ]
      }
  ]
}
```

**Custom Slot Types**:
Type: Groups
Values:
```
living room
andrews room```

**Sample Utterances**:
```
ActivateIntent turn on {Group}
ActivateIntent turn {Group} on
```

In the above intent, our intent name is **ActivateIntent**, the custom slot type is **Groups** and our custom slot value will be referenced as **Group**.

So what is a *custom slot*? A custom slot allows us to pass a different value to our Home Assistant setup. Essentially, this sets a variable that is passed to HASS, so that we can use one intent as as template to do more functions. 


Now let's look at the HASS Alexa YAML.

**alexa.yaml**:
```
intents:
  ActivateIntent:
    action:
      - service: homeassistant.turn_on
        data_template:
          entity_id: group.{{ Group | replace(" ", "_") }}
    speech:
      type: plaintext
      text: Turned on {{ Group }}
```

So this is actually pretty simple. We see that intent name, **ActivateIntent** is referenced, along with an **action** and a **speech** section. 

With this intent, we are turning on a group, passed to Home Assistant as {{ Group }} (using HASS Jinja2 templating language). This is essentially just an automation, but is triggered by Amazon's API. The **speech** section is what Alexa will speak back to us when the intent is activated. 

This might be a little confusing, so below I've pasted the call that Amazon's API actually makes to Home Assistant (this is from the "Service Simulator" section found in the "Test" section of the Alexa API skill setup).

Here is the Service Request displayed when entering "tell home assistant to turn on living room" as an utterenace (this is what you will speak to Alexa).

```
...
...
...
  "request": {
    "type": "IntentRequest",
    "requestId": "EdwRequestId.7bb3b239-0e0e-4413-b365-2302d64f527a",
    "locale": "en-US",
    "timestamp": "2016-12-23T03:11:49Z",
    "intent": {
      "name": "ActivateIntent",
      "slots": {
        "Group": {
          "name": "Group",
          "value": "living room"
        }
      }
    }
  },
  "version": "1.0"
}
```

I've cut out some of the extraneous info above, but you can see that Amazon figured out we want to use *ActivateIntent* (because of the utterance) and it set the variable *Group* to the string "living room". 

In this case, Home Assistant responded with:

```
{
  "version": "1.0",
  "response": {
    "outputSpeech": {
      "type": "PlainText",
      "text": "Turned on living room"
    },
    "shouldEndSession": true
  },
  "sessionAttributes": {}
}
```

It worked :)

 
