# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import asyncio
import omni.ext
import omni.kit.app

import carb
import carb.settings
import carb.dictionary
import carb.events
import carb.tokens
import carb.input
import omni.usd
import omni.client.utils
import omni.kit.livestream.messaging as messaging
from omni.kit.viewport.utility import get_active_viewport_camera_string

from pxr import UsdGeom, Usd

# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class Messaging():
    def on_startup(self):
        # Internal messaging state
        self._is_external_update: bool = False
        self._open_stage_url: str = ""
        self._camera_attrs = {}
        self._subscriptions = []

        # -- register outgoing events/messages
        outgoing = [
            "stageSelectionChanged",     # notify when user selects something in the viewport.
            "openedStageResult",         # notify when USD Stage has loaded.
            "getChildrenResponse",       # response to request for children of a prim
            "makePrimsPickableResponse", # response to request for primitive being pickable.
            "resetStageResponse",        # response to the request to reset camera attributes
            "updateProgressAmount",      # Status bar event denoting progress
            "updateProgressActivity",    # Status bar event denoting current activity
        ]

        for o in outgoing:
            messaging.register_event_type_to_send(o)

        # -- register incoming events/messages
        incoming = {
            'openStageRequest': self._on_open_stage,                  # request to open a stage
            'getChildrenRequest': self._on_get_children,              # request to get children of a prim
            'selectPrimsRequest' : self._on_select_prims,             # request to select a prim
            'makePrimsPickable' : self._on_make_pickable,             # request to make primitives pickable
            'resetStage' : self._on_reset_camera,                     # request to make primitives pickable
            "omni.kit.window.status_bar@progress": self._on_progress, # internal event to capture progress status
            "omni.kit.window.status_bar@activity": self._on_activity, # internal event to capture progress activity
        }

        for event_type, handler in incoming.items():
            self._subscriptions.append(
                omni.kit.app.get_app().get_message_bus_event_stream().create_subscription_to_pop(
                    handler, name=event_type
                )
            )

        # -- subscribe to stage events
        event_stream = omni.usd.get_context().get_stage_event_stream()
        self._subscriptions.append(
            event_stream.create_subscription_to_pop(self._on_stage_event)
        )

    def _on_open_stage(self, event: carb.events.IEvent) -> None:
        """
        Handler for `openStageRequest` event.

        Kicks off stage loading from a given URL, will send success if the layer is already loaded, and an error on any failure.
        """
        if event.type == carb.events.type_from_string("openStageRequest"):
            if "url" not in event.payload:
                carb.log_error(
                    f"Unexpected message payload: missing \"url\" key. Payload: '{event.payload}'")
                return

            def process_url(url):
                # Using a single leading `.` to signify that the path is relative to the ${app} token's parent directory.
                if url.startswith(("./", ".\\")):
                    return carb.tokens.acquire_tokens_interface().resolve("${app}/.." + url[1:])
                return url

            # Check to see if we've already loaded the current stage.
            url = process_url(event.payload["url"])
            current_stage = omni.usd.get_context().get_stage().GetRootLayer().identifier

            # If we are, we don't need to reload the file, instead we'll just send the success message.
            if omni.client.utils.equal_urls(url, current_stage):
                message_bus = omni.kit.app.get_app().get_message_bus_event_stream()
                event_type = carb.events.type_from_string("openedStageResult")
                payload = {"url": url, "result": "success", "error": ''}
                message_bus.dispatch(event_type, payload=payload)
                message_bus.pump()
                self._open_stage_url = ""
                return

            carb.log_info(f"Received message to load '{url}'")

            # Aysncly load the incoming stage
            async def open_stage():
                result, error = await omni.usd.get_context().open_stage_async(
                    url,
                    load_set=omni.usd.UsdContextInitialLoadSet.LOAD_ALL
                )
                if result is True:
                    self._open_stage_url = url
                else:
                    # Let the streamer know that loading failed.
                    carb.log_error(f"Failed to open stage: {error}")
                    message_bus = omni.kit.app.get_app().get_message_bus_event_stream()
                    event_type = carb.events.type_from_string("openedStageResult")
                    payload = {"url": url, "result": "error", "error": error}
                    message_bus.dispatch(event_type, payload=payload)
                    message_bus.pump()

            asyncio.ensure_future(open_stage())

    def get_children(self, prim_path, filters=None):
        """
        Collect any children of the given `prim_path`, potentially filtered by `filters`
        """
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(prim_path)

        filter_types = {
            "USDGeom": UsdGeom.Mesh,
            "mesh": UsdGeom.Mesh,
            "xform": UsdGeom.Xform,
            "scope": UsdGeom.Scope,
        }

        children = []
        for child in prim.GetChildren():
            # If a child doesn't pass any filter, we skip it.
            if filters is not None:
                if not any(child.IsA(filter_types[filt]) for filt in filters if filt in filter_types):
                    continue

            child_name = child.GetName()
            child_path = str(prim.GetPath())
            # Skipping over cameras
            if child_name.startswith('OmniverseKit_'):
                continue
            # Also skipping rendering primitives.
            if prim_path == '/' and child_name == 'Render':
                continue
            child_path = child_path if not child_path == '/' else ''
            carb.log_info(f'child_path: {child_path}')
            info = {"name": child_name, "path": f'{child_path}/{child_name}'}

            # We return an empty list here to indicate that children are available, but
            # the current app does not support pagination, so we use this to lazy load the stage tree.
            if child.GetChildren():
                info["children"] = []

            children.append(info)

        return children

    def _on_get_children(self, event: carb.events.IEvent) -> None:
        """
        Handler for the `getChildrenRequest` event
        Collects a filtered collection of a given primitives children.
        """
        if event.type == carb.events.type_from_string("getChildrenRequest"):
            carb.log_info(f"Received message to return list of a prim\'s children")
            message_bus = omni.kit.app.get_app().get_message_bus_event_stream()
            event_type = carb.events.type_from_string("getChildrenResponse")
            children = self.get_children(prim_path=event.payload["prim_path"], filters=event.payload["filters"])
            for o in children:
                print(o)
            payload = {
                "prim_path" : event.payload["prim_path"],
                "children": children
            }
            message_bus.dispatch(event_type, payload=payload)
            message_bus.pump()

    def _on_select_prims(self, event: carb.events.IEvent) -> None:
        """
        Handler for `selectPrimsRequest` event.

        Selects the given primitives.
        """
        if event.type == carb.events.type_from_string("selectPrimsRequest"):
            new_selection = []
            if "paths" in event.payload:
                new_selection = list(event.payload["paths"])
                carb.log_info(f"Received message to select '{new_selection}'")
            # Flagging this as an external event because it was initiated by the client.
            self._is_external_update = True
            sel = omni.usd.get_context().get_selection()
            sel.clear_selected_prim_paths()
            sel.set_selected_prim_paths(new_selection, True)

    def _on_stage_event(self, event):
        """
        Hanles all stage related events.

        `omni.usd.StageEventType.SELECTION_CHANGED`: Informs the StreamerApp that the selection has changed.
        `omni.usd.StageEventType.ASSETS_LOADED`: Informs the StreamerApp that a stage has finished loading its assets.
        `omni.usd.StageEventType.OPENED`: On stage opened, we collect some of the camera properties to allow for them to be reset.

        """
        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            # If the selection changed came from an external event, we don't need to let the streaming client know
            # because it initiated the change and is already aware.
            if self._is_external_update:
                self._is_external_update = False
            else:
                message_bus = omni.kit.app.get_app().get_message_bus_event_stream()
                event_type = carb.events.type_from_string("stageSelectionChanged")
                payload = {"prims": omni.usd.get_context().get_selection().get_selected_prim_paths()}
                message_bus.dispatch(event_type, payload=payload)
                message_bus.pump()
                carb.log_info(f"Selection changed: Path to USD prims currently selected = {omni.usd.get_context().get_selection().get_selected_prim_paths()}")

        elif event.type == int(omni.usd.StageEventType.ASSETS_LOADED):
            if self._open_stage_url:
                # Inform the streaming client that the stage has finished loading all assets.
                message_bus = omni.kit.app.get_app().get_message_bus_event_stream()
                event_type = carb.events.type_from_string("openedStageResult")
                payload = {"url": self._open_stage_url, "result": "success", "error": ''}
                message_bus.dispatch(event_type, payload=payload)
                message_bus.pump()
                self._open_stage_url = ""

        elif event.type == int(omni.usd.StageEventType.OPENED):
            # Set the entire stage to not be pickable.
            ctx = omni.usd.get_context()
            ctx.set_pickable("/", False)
            # Clear before using, so that we're sure the data is only from the new stage.
            self._camera_attrs.clear()
            # Capture the active camera's camera data, used to reset the scene to a known good state.
            if (prim := ctx.get_stage().GetPrimAtPath(get_active_viewport_camera_string())):
                for attr in prim.GetAttributes():
                    self._camera_attrs[attr.GetName()] = attr.Get()

    def _on_reset_camera(self, event: carb.events.IEvent):
        """
        Handler for `resetStage` event.

        Resets the camera back to values collected when the stage was opened.
        A success message is sent if all attributes are succesfully reset, and error message is set otherwise.
        """
        if event.type == carb.events.type_from_string("resetStage"):
            ctx = omni.usd.get_context()
            stage = ctx.get_stage()
            try:
                # Reset the camera.
                # The camera lives on the session layer, which has a higher opinion than the root stage.
                # So we need to explicitly target the session layer when resetting the camera's attributes.
                camera_prim = ctx.get_stage().GetPrimAtPath(get_active_viewport_camera_string())
                edit_context = Usd.EditContext(stage, Usd.EditTarget(stage.GetSessionLayer()))
                with edit_context:
                    for name, value in self._camera_attrs.items():
                        attr = camera_prim.GetAttribute(name)
                        attr.Set(value)
            except Exception as e:
                payload = {"result": "error", "error": str(e)}
            else:
                payload = {"result": "success", "error": ""}
            message_bus = omni.kit.app.get_app().get_message_bus_event_stream()
            event_type = carb.events.type_from_string("resetStageResponse")
            message_bus.dispatch(event_type, payload=payload)
            message_bus.pump()

    def _on_make_pickable(self, event: carb.events.IEvent):
        """
        Handler for `makePrimsPickable` event.

        Enables viewport selection for the provided primitives.
        Sends 'makePrimsPickableResponse' back to streamer with current success status.
        """
        if event.type == carb.events.type_from_string("makePrimsPickable"):
            message_bus = omni.kit.app.get_app().get_message_bus_event_stream()
            event_type = carb.events.type_from_string("makePrimsPickableResponse")
            try:
                paths = event.payload['paths'] or []
                for path in paths:
                    omni.usd.get_context().set_pickable(path, True)
            except Exception as e:
                payload = {"result": "error", "error": str(e)}
            else:
                payload = {"result": "success", "error": ""}
            message_bus.dispatch(event_type, payload=payload)
            message_bus.pump()

    def _on_progress(self, event: carb.events.IEvent):
        """
        Handler for `omni.kit.window.status_bar@progress` event.
        This forwards the statusbar progress events to the streaming client.
        """
        if not self._open_stage_url:
            return
        if event.type == carb.events.type_from_string("omni.kit.window.status_bar@progress"):
            message_bus = omni.kit.app.get_app().get_message_bus_event_stream()
            event_type = carb.events.type_from_string("updateProgressAmount")
            # event.payload.get_dict() is used to capture a copy of the incoming event's payload as a python dictionary
            message_bus.dispatch(event_type, payload=event.payload.get_dict())
            message_bus.pump()

    def _on_activity(self, event: carb.events.IEvent):
        """
        Handler for `omni.kit.window.status_bar@activity` event.
        This forwards the statusbar activity events to the streaming client.
        """
        if not self._open_stage_url:
            return
        if event.type == carb.events.type_from_string("omni.kit.window.status_bar@activity"):
            message_bus = omni.kit.app.get_app().get_message_bus_event_stream()
            event_type = carb.events.type_from_string("updateProgressActivity")
            # event.payload.get_dict() is used to capture a copy of the incoming event's payload as a python dictionary
            message_bus.dispatch(event_type, payload=event.payload.get_dict())
            message_bus.pump()

    def on_shutdown(self):
        # Reseting the state.
        self._subscriptions.clear()
        self._is_external_update: bool = False
        self._open_stage_url: str = ""
        self._camera_attrs.clear()
