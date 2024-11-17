# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.ext
from omni.ui import Menu, AbstractItem, AbstractValueModel
import omni.ui as ui
import carb
import asyncio

from functools import partial

# import carb.settings



from .applicationenvironment import applicationenvironment
from .stageinterface import StageInterface
from .omnikafkainterface import OmniKafkaInterface



# Functions and vars are available to other extensions as usual in python: `dstg.babylon.some_public_function(x)`
def some_public_function(x: int):
    print(f"[dstg.babylon] some_public_function was called with {x}")
    return x ** x


# Any class derived from `omni.ext.IExt` in the top level module (defined in `python.modules` of `extension.toml`) will
# be instantiated when the extension gets enabled, and `on_startup(ext_id)` will be called.
# Later when the extension gets disabled on_shutdown() is called.
class Babylon5(omni.ext.IExt):
    # ext_id is the current extension id. It can be used with the extension manager to query additional information,
    # like where this extension is located on the filesystem.

    WINDOW_CONFIG = {
        "width": 400,  # Default window width
        "height": 500,  # Default window height
        "min_width": 300,  # Minimum window width
        "min_height": 200,  # Minimum window height
    }

    LAYOUT_CONFIG = {
        "name_width_percent": 30,  # Width of name column as percentage
        "value_width_percent": 70,  # Width of value column as percentage
        "row_height": 25,          # Height of each attribute row
        "row_spacing": 2,          # Spacing between rows
        "section_spacing": 10,     # Spacing between major sections
        "max_visible_rows": 10,    # Number of rows visible before scrolling
    }




    async def async_connect(self):
        try:
            self._status_label.text = "Connecting..."
            await applicationenvironment.Omni_Kafka_Interface.connect()
            self._status_label.text = "Connected"
            print("[dstg.babylon] Successfully connected to Kafka")
        except Exception as e:
            self._status_label.text = "Connection Failed"
            print(f"[dstg.babylon] Failed to connect to Kafka: {str(e)}")

    def on_startup(self, ext_id):
        print("[dstg.babylon] Extension startup")

        self._count = 0

        self._window = ui.Window("Metadata", width=self.WINDOW_CONFIG["width"],
                                            height=self.WINDOW_CONFIG["height"],
                                            min_width=self.WINDOW_CONFIG["min_width"],
                                            min_height=self.WINDOW_CONFIG["min_height"])
        self._context_actions = {
            "Copy Value": self._copy_value,
            "Reset to Default": self._reset_to_default,
            "Show History": self._show_history,
            "Print Hello": self._print_hello,
            # Add more actions as needed
        }

        self._setup_ui()

        applicationenvironment.Stage_Interface = StageInterface(self)

        applicationenvironment.Omni_Kafka_Interface = OmniKafkaInterface()

        # Schedule the async connection
        asyncio.ensure_future(self.async_connect())



    def _setup_ui(self):
        with self._window.frame:
            with ui.VStack(spacing=self.LAYOUT_CONFIG["section_spacing"]):
                # Status section
                self._status_label = ui.Label("Not Connected")

                # Attributes section
                with ui.VStack(spacing=5):
                    ui.Label("Object Attributes", alignment=ui.Alignment.CENTER)

                    # Calculate scrolling frame height based on desired visible rows
                    scroll_height = (self.LAYOUT_CONFIG["row_height"] +
                                   self.LAYOUT_CONFIG["row_spacing"]) * \
                                   self.LAYOUT_CONFIG["max_visible_rows"]

                    with ui.ScrollingFrame(height=scroll_height):
                        self._attribute_stack = ui.VStack(spacing=self.LAYOUT_CONFIG["row_spacing"])

                # Counter section
                self._setup_counter()

    def _setup_counter(self):
        self._count = 0
        label = ui.Label("empty")

        def on_click():
            self._count += 1
            label.text = f"count: {self._count}"

        def on_reset():
            self._count = 0
            label.text = "empty"

        with ui.HStack(spacing=5):
            ui.Button("Add to total", clicked_fn=on_click)
            ui.Button("Reset total", clicked_fn=on_reset)

       # self.set_settings()

    def _create_context_menu(self, attr):
        """Create and show context menu for an attribute"""
        # Create a context menu as a class member if not already created
        if not hasattr(self, '_context_menu'):
            self._context_menu = ui.Menu()

        # Clear any existing items
        self._context_menu.clear()

        # Populate the menu
        with self._context_menu:
            # Add standard actions
            for action_name, action_fn in self._context_actions.items():
                ui.MenuItem(action_name, triggered_fn=lambda a=attr, f=action_fn: f(a))

            # Add type-specific actions in a submenu
            if attr["type"] in ["float", "int"]:
                with ui.Menu("Numeric Operations"):
                    ui.MenuItem("Plot History", clicked_fn=lambda: self._plot_numeric_history(attr))
                    ui.MenuItem("Show Statistics", clicked_fn=lambda: self._show_statistics(attr))

            elif attr["type"] == "string":
                with ui.Menu("Text Operations"):
                    ui.MenuItem("Edit Text", triggered_fn=lambda: self._edit_text_value(attr))

            # Add custom actions if defined
            custom_actions = attr.get("custom_actions", {})
            if custom_actions:
                with ui.Menu("Custom Actions"):
                    for action_name, action_fn in custom_actions.items():
                        ui.MenuItem(action_name, triggered_fn=lambda a=attr: action_fn(a))

        return self._context_menu

    def _create_attribute_row(self, attr):
        """Create a single attribute row with context menu support"""
        with ui.HStack(height=self.LAYOUT_CONFIG["row_height"]) as row:
            # Make the entire row interactive


            #row.set_mouse_pressed_fn(lambda x, y, button, modifier, attr=attr: self._handle_row_click(x, y, button, modifier, attr))
            row.set_mouse_pressed_fn(partial(self._handle_row_click, attr=attr))


            # Name column
            with ui.HStack(width=ui.Percent(self.LAYOUT_CONFIG["name_width_percent"])):
                ui.Label(
                    attr["name"],
                    word_wrap=True,
                    alignment=ui.Alignment.LEFT_TOP
                )

            # Value column
            with ui.HStack(width=ui.Percent(self.LAYOUT_CONFIG["value_width_percent"])):
                value_str = self._format_value(attr["value"], attr["type"])
                ui.Label(
                    value_str,
                    word_wrap=True,
                    alignment=ui.Alignment.LEFT_TOP
                )

    def _handle_row_click(self, x, y, button, modifier, attr):
        """Handle mouse clicks on attribute rows"""
        if button == 1: # ui.MouseButton.RIGHT:
            menu = self._create_context_menu(attr)
            menu.show()

    def refresh_attributes(self, attributes):
        self._attribute_stack.clear()

        with self._attribute_stack:
            for attr in attributes:
                self._create_attribute_row(attr)

    def _format_value(self, value, attr_type):
        """Format the value based on its type"""
        if attr_type == "number":
            return f"{float(value):.2f}"
        elif attr_type == "vector3":
            return f"({value[0]:.1f}, {value[1]:.1f}, {value[2]:.1f})"
        elif attr_type == "boolean":
            return str(value)
        elif attr_type == "color":
            return f"RGB({value[0]:.2f}, {value[1]:.2f}, {value[2]:.2f})"
        else:
            return str(value)


    def _print_hello(self, attr):
        print("hello: " + attr)

    def _copy_value(self, attr):
        """Copy attribute value to clipboard"""
        value_str = self._format_value(attr["value"], attr["type"])
        ui.ClipboardHelper.copy(value_str)

    def _reset_to_default(self, attr):
        """Reset attribute to default value"""
        if "default" in attr:
            # Implement reset logic here
            pass

    def _show_history(self, attr):
        """Show attribute value history"""
        # Implement history display logic here
        pass

    def _plot_numeric_history(self, attr):
        """Plot history for numeric attributes"""
        # Implement plotting logic here
        pass

    def _show_statistics(self, attr):
        """Show statistics for numeric attributes"""
        # Implement statistics display logic here
        pass

    def _edit_text_value(self, attr):
        """Open text editor for string attributes"""
        # Implement text editing logic here
        pass


    def add_context_action(self, name, action_fn):
        """Add a custom context menu action"""
        self._context_actions[name] = action_fn


 #   def set_settings(self):
 #       settings = carb.settings.get_settings()
 #       settings.set("/persistent/ext/omni.kit.widget.stage/show_prim_displayname", True)

   # def on_shutdown(self):
   #     applicationenvironment.Stage_Interface.stage_event_sub = None
       # asyncio.ensure_future(applicationenvironment.Omni_Kafka_Interface.disconnect())

    #
    #     print("[dstg.babylon] Extension shutdown")

    async def async_shutdown(self):
        """Separate async method to handle shutdown operations"""
        try:
            await applicationenvironment.Omni_Kafka_Interface.disconnect()
        except Exception as e:
            print(f"[dstg.babylon] Error during Kafka disconnect: {e}")
        finally:
            applicationenvironment.Stage_Interface.stage_event_sub = None
            print("[dstg.babylon] Extension shutdown complete")

    def on_shutdown(self):
        """Main shutdown method"""
        # Create event loop if it doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the async shutdown
        if loop.is_running():
            # If loop is running, schedule the shutdown
            asyncio.ensure_future(self.async_shutdown())
        else:
            # If loop is not running, run it until complete
            loop.run_until_complete(self.async_shutdown())

        print("[dstg.babylon] Extension shutdown initiated")