# Omniverse USD Viewer Sample Application

<p align="center">
  <img src="usd_viewer_template/sample.png" width=100% />
</p>

This sample is part of the larger `Omniverse Embedded Web Viewer Example`.
The sample demonstrates how a Kit application generated from the USD Viewer
template can be created for streaming into a front end client and how to send
messages back and forth between the two apps.

## Prerequisites

- [Technical Requirements](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/common/technical-requirements.html).
- Python skills.

## Quick Start

Refer to [README Quick Start](../../README.md#quick-start) to get setup and choose the `USD Viewer`
template when you create the application using `repo template new`.

When the application launches it initializes streaming and messaging, but otherwise it remains idle.
Refer to the `Omniverse Embedded Web Viewer Example` documentation for also launching a web-viewer-sample
that connects with the USD Viewer application.

## USD Viewer Development

The `USD Viewer Template` is a starting point for creating streamed Kit applications. You should
of course name the application anything you want but for this document we will refer to the
application as `USD Viewer`.

USD Viewer is configured to use the `omni.kit.livestream.webrtc` Kit extension to enable
streaming and messaging. The custom messaging functionality is added by
`omni.kit.livestream.messaging`. If you for any reason choose to not use the USD Viewer Template
as a starting point then those two Extensions are critical to add as dependencies.

USD Viewer messaging is implemented within the `my_company.my_usd_viewer.setup` extension's `messaging.py` module.
As a developer you are of course free to organize the messaging capabilities as you see fit.
You can create as many Extensions as you’d like. For example, you could have one for managing
what asset is loaded and another for managing the USD Stage state.

|                 | Kit Extension                    | Functionality                                         |
|-----------------|----------------------------------|-------------------------------------------------------|
| Implementation  | `my_company.my_usd_viewer.setup` | Sends and/or receives JSON formatted custom messages. |
| Kit SDK         | `omni.kit.livestream.webrtc`     | Enables streaming and messaging.                      |
| Kit SDK         | `omni.kit.livestream.messaging`  | Enables JSON formatted custom messages.               |

Developing a USD Viewer is about managing dependencies and settings in the application `.kit` file. Creating
custom capabilities is done by adding custom extensions.

## Kit Messaging Extension Development

This sample provides custom capabilities such as opening a file per client request, providing information
about the USD Stage, and notifying the client about selection changes. These sample messages are just that - samples.
You can create whatever messages you want to and then implement handlers to make changes to the USD Stage, notify
about changes, or even request information from the client.

When you create a new Extension such as `my_company.my_usd_viewer.setup` to support messaging there are a few critical steps involved:

1. Make sure `omni.kit.livestream.messaging` is listed in the `[dependencies]` section of the `./source/extensions/[extension name]/config/extension.toml` file:

```toml
[dependencies]
"omni.kit.livestream.messaging" = {}
```

2. Import these Extensions in your messaging Extension Python file:

```python
import carb
import omni.kit.app
import omni.kit.livestream.messaging as messaging
```

You are now ready to implement the sending and receiving of messages.

### Message Format

All custom messages exchanged between `USD Viewer` and the front end client follows the same format:
an object with properties `event_type` and `payload` that is JSON stringified prior to being sent off.
The string serialization is handled automatically on the Kit side.

```python
{
    event_type: "myEvent",
    payload: {
        property_name  : value
    }
}
```

### Send a Custom Message

To send a message you first need to make sure the `event_type` is registered with the `omni.kit.livestream.messaging` Extension:

```python
messaging.register_event_type_to_send('myEvent')
```

With the `event_type` registered, you can use a snippet like the one below for sending a custom message:

```python
# Acquire the message bus
message_bus = omni.kit.app.get_app().get_message_bus_event_stream()
# Generate the event_type
event_type = carb.events.type_from_string("myEvent")
# Put some message data into a payload
payload = {'some_key': 'some value', 'another_key': 52}
# Queue up the message
message_bus.dispatch(event_type, payload=payload)
# Send message
message_bus.pump()
```

That’s all there is to it. Message is sent to be handled by the front end client.

### Receive a Custom Message

To receive messages from the front end client you need to subscribe to the Kit event message bus and provide a handler function:

```python
# Subscribe to an event from front-end-client
self._client_request_subscription = omni.kit.app.get_app().get_message_bus_event_stream().create_subscription_to_pop(self._client_request_handler, name='client_request')
```

The handler should check the event type and then handle the message appropriately:

```python
def _on_reset_camera(self, event: carb.events.IEvent):
    if event.type == carb.events.type_from_string('client_request'):
        # Do something
        …
        # Perhaps send a message back to confirm the request was handled.
        …
```

Finally, the Extension needs to let go of the subscription pointer on Extension shutdown:

```python
def on_shutdown(self):
    self._client_request_subscription = None
```

### Sample Message Loop

Let's take a look at a message loop handled in [messaging.py](../../templates/extensions/usd_viewer.setup/template/{{python_module_path}}/messaging.py).

The `_on_open_stage()` function is registered as a handler for the `openStageRequest` `event_type` in the `on_startup()` function.

When a request with that `event_type` is sent from the front end client the `_on_open_stage()` function is invoked. This
triggers the loading of the provided file URL and the extension starts sending progress notifications to the client
from within `_on_progress()` and `_on_activity()`. Once the entire file has loaded the `_on_stage_event()` reacts to the
`omni.usd.StageEventType.ASSETS_LOADED` event and sends a message to the client with the `event_type` `openedStageResult`.

That example is one of the more advanced ones in this sample but highlights how USD Viewer can keep the client informed
throughout complex processes.

That completes the instructions for Kit messaging extension development. We covered the important dependencies and how to
exchange messages with the front end client. With this you can continue developing the message handlers to return information
about the USD Stage and apply changes to it per client requests.

## Known Issues

- There are 2 build errors for dependencies `omni.replicator.agent.core` and `'omni.anim.people`. The errors does not affect the USD Viewer. Ignore these.
