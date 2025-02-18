
import logging
from contextlib import contextmanager # type: ignore
from typing import List
import os.path

import omni.usd
import omni.ui

from typing import Any, Callable, Dict

import carb


from pxr import Usd, UsdGeom, Gf, Sdf

import asyncio

from .applicationenvironment import applicationenvironment

from .ActivationManager import ActivationManager

from functools import partial


logger = logging.getLogger(__name__)



class StageInterface(object):
    """
    A class to manage interactions with the Omniverse stage (thanks Aleck!)
    Attributes:
    -----------

    _stage : object
        The current Omniverse stage object.
    _s_h_window : object
        The main window for the extension which holds all the 'global' data, suchas the Vuln_Dict.

    """



    def __init__(self, extension: 'Babylon5'):
        super().__init__()
        self.get_stage()
        self.activations = None
        self.extension = extension
        self.subscribe_to_stage_selection_changes()
       # self.visibility_mgr = VisibilityManager()

    @property
    def stage(self):
        self.get_stage()
        return self._stage

    @stage.setter
    def stage(self, value):
        self._stage = value

    @property
    def context(self):
        self.get_stage()
        return self._context

    @context.setter
    def context(self, value):
        self._context = value

    def get_stage(self):
        """
        Retrieve and store the current Omniverse stage.
        """
        self._context = omni.usd.get_context()
        self._stage = self._context.get_stage()

    def load_usd_file(self, file_path=None):
        self.context.close_stage()

        if file_path is None:
            self.context.new_stage()
        else:
            self.context.open_stage(file_path)

        self.get_stage()

    def filter_invalid_ids(self, ids):
        return [id_ for id_ in ids if Node.is_eq_id(id_)]


    def subscribe_to_stage_selection_changes(self):
        self._events = self.context.get_stage_event_stream()

        self.stage_event_sub = self._events.create_subscription_to_pop(
                                    self._on_stage_event,
                                    name='Stage Event Update'
                                    )

    def _on_stage_event(self, event):
        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            self._on_selection_changed()

    def _on_selection_changed(self):

        carb.log_info("on selection changed")

        selection = self.context.get_selection().get_selected_prim_paths()
        if len(selection) < 1:
            return


        element_prims = [self.stage.GetPrimAtPath(e) for e in selection]
       # object_types = [e.GetAttribute("objectType").Get() for e in element_prims]
        target = element_prims[0]

        # GUI: we have a type that is xform and a name that is mesh_D_Solid then revert to the parent in the selection!

        print(target.GetTypeName())
        print(target.GetName().split("/")[-1])

        if ((target.GetTypeName() == "Mesh") or ((target.GetTypeName() == "Xform") and (target.GetName().split("/")[-1] == "mesh_D_Solid"))):  # meshes don't have any info so go to the parent which will!
            target = target.GetParent()
            self.context.get_selection().set_prim_path_selected(str(target.GetPath()), True, True, True)
        print("path: ")
        print(target.GetPath())
        print(str(target.GetPath()).removeprefix("/World/CCPB_811_816_Whole_boat/"))
        print("Name: " + target.GetName())

        # testquery = f"[:find ?entityid :where [?entityid :object/name \"{element_prims[0].GetName()}\"]]
        name = str(target.GetPath()).removeprefix("/World/CCPB_811_816_Whole_boat/")

        testquery = f"[:find ?entityid ?property-name ?value ?value-type ?property-group :in $ :where [?entityid :object/name \"{name}\"] [?entityid :object/properties ?prop] [?prop :property/group ?property-group] [?prop :property/name ?property-name] (or-join [?prop ?value ?value-type] (and [?prop :property/value ?value] [(ground :property/value) ?value-type]) (and [?prop :property/string-value ?value] [(ground :property/string-value) ?value-type]) (and [?prop :property/int-value ?value] [(ground :property/int-value) ?value-type]) (and [?prop :property/float-value ?value] [(ground :property/float-value) ?value-type]) (and [?prop :property/bool-value ?value] [(ground :property/bool-value) ?value-type]) (and [?prop :property/entity-value ?value] [(ground :property/entity-value) ?value-type]) (and [?prop :property/vector-value ?value] [(ground :property/vector-value) ?value-type]))]"

        kafka_interface = applicationenvironment.Omni_Kafka_Interface

        print("Sending Request")

        asyncio.ensure_future(kafka_interface.query_request(database= "ECCPBDB", query=testquery, response= lambda value: self.extension.refresh_attributes(self.process_query_result(value))))

    def process_query_result(self, message_dict):

        carb.log_info("Processing Query Result")

        # Extract kwargs from the dictionary
        kwargs = message_dict.get('kwargs', {})

        # Check if this is a QueryResult operation
        if kwargs.get('operation') != 'QueryResult':
            return None

        # Extract the Result list
        result_list = kwargs.get('Result', [])

        # Transform each sublist into a dictionary
        processed_attributes = []
        for item in result_list:
            if len(item) == 5:  # Ensure we have all required elements
                attribute_dict = {
                    'entity': item[0],
                    'name': item[1],
                    'value': item[2],
                    'type': item[3],
                    'group': item[4]
                }
                processed_attributes.append(attribute_dict)

        return processed_attributes

    def process_manual_query_result(self, message_dict):

        carb.log_info("Processing Manual Query Result")

        if not self.activations or not self.activations.stage:
            self.activations = ActivationManager(self._stage) # redo activation if it doesn't exist or the stage isnt set

        # Extract kwargs from the dictionary
        kwargs = message_dict.get('kwargs', {})

        # Check if this is a QueryResult operation
        if kwargs.get('operation') != 'QueryResult':
            return None

        # Extract the Result list
        result_list = kwargs.get('Result', [])

        toplevel = "/World/CCPB_811_816_Whole_boat"

        #
        # self.make_visible(["/World/CCPB_811_816_Whole_boat/" + original for original in result_list])
        # omni.usd.commands.ToggleVisibilitySelectedPrimsCommand(["/World/CCPB_811_816_Whole_boat/" + original for original in result_list], self._stage) #,true
        #if self.visiblity_state_cache:
        #    self.visibility_mgr.restore_visibility(self._stage)

        #self.visibility_mgr.set_visibility_for_all_except(self._stage, ["/World/CCPB_811_816_Whole_boat/" + original for original in result_list])

        #self.toggle_viewport_visibility(self._stage, ["/World/CCPB_811_816_Whole_boat/" + original for original in result_list])

        self.activations.activate(toplevel, [toplevel + "/" + original for original in result_list])
        print("Message processing finished")


    def toggle_viewport_visibility(self, stage, visible_paths):

        import omni.kit.viewport.utility as vp_utils

        viewport_api = vp_utils.get_active_viewport()
        if viewport_api:
            viewport_api.draw_mode = "wireframe"
            omni.kit.viewport.actions.toggle_mesh_visibility()

        omni.kit.commands.execute('ToggleVisibilitySelectedPrims',
            selected_paths=visible_paths,
            state=True)

 #   def _on_equipment_select(self, eq_id):

  #      applicationenvironment.Systems_Hierarchy_Window.Tree_View.clear_selection()
   #     applicationenvironment.Systems_Hierarchy_Window.Tree_View.model.refresh()

    #    eq_node = applicationenvironment.Systems_Hierarchy_Window.Tree_View.model.graph.get_equipmentid(eq_id)

     #   applicationenvironment.Information_Window.rebuild_tabs(eq_node)
