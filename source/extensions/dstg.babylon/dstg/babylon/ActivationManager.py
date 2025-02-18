

from pxr import Usd, UsdGeom, Sdf
import omni.usd

import carb
import time
# import usd_visibility

class ActivationManager:
    def __init__(self, stage):
        self.deactivated_prims = set()
        self.stage = stage
        self.dirty = False
        self._change_block = None
        self.session_layer = None


    def activate(self, start, PrimPaths):
        targets = set()
        carb.log_info("Building targets")

        for primpath in PrimPaths:
            targets.update(self.generate_prim_hierarchy(primpath))

        carb.log_info("activating targets")

        self.activatePrimsOnly(start, targets) # given a set of prims paths only activate (but record deactivations)



    def activate2(self, start, PrimPaths):
        self.activatePrimsOnly(start, set().union(*map(self.generate_prim_hierarchy, PrimPaths)))  # probably slower!

        #      for path in self.deactivated_prims:
        #          prim = self.stage.GetPrimAtPath(path)
        #          if prim.IsValid():
        #              self.change_state(prim) # default true!
        #      self.deactivated_prims = set()

    # def restoreActivations(self):
    #     carb.log_info("restoring activations")
    #     if self.dirty:
    #         if self.stage:
    #             session_layer = self.stage.GetSessionLayer()
    #             if session_layer:
    #                 session_layer.Clear()
    # #              self.stage.GetSessionLayer().Reload()
    #                 self.dirty = False
    #                 print("Session layer cleared. Changes reverted.")


    def begin_batch(self):
        """Start a batch edit operation"""
        self._change_block = Sdf.ChangeBlock()
        self._change_block.__enter__()

    def end_batch(self):
        """Commit batch edits"""
        self._change_block.__exit__(None, None, None)
        self._change_block = None

    def generate_prim_hierarchy(self, path):
        parts = path.strip('/').split('/')
        return ['/' + '/'.join(parts[:i + 1]) for i in range(len(parts))]



    # def deactivate_children(self, start_prim_path, keep_active_set):
    #     """
    #     Traverse and deactivate children of start_prim_path not in keep_active_set.
    #     """
    #     if start_prim_path == None:
    #         carb.log_info("starting with a none!")
    #     else:
    #         #print("Prim Path: " + start_prim_path)
    #         prim = self.stage.GetPrimAtPath(start_prim_path)

    #         # Ensure valid and active starting prim
    #         if not prim.IsValid() or not prim.IsActive():
    #             print(f"Skipping invalid or inactive prim: {start_prim_path}")
    #             return

    #         # Traverse children and process
    #         for child in prim.GetFilteredChildren(Usd.TraverseInstanceProxies(Usd.PrimIsActive & Usd.PrimIsDefined & ~Usd.PrimIsAbstract)):
    #             child_path = str(child.GetPath())
    #             if child.GetTypeName() != "Mesh": # dont't turn off the meshes! (turning off the parents will do what we want!)
    #                 # If child path is not in keep_active_set, deactivate and record
    #                 if child_path not in keep_active_set:
    #                     if "Looks" not in child_path:

    #                             if child.IsActive():
    #                                 self.change_state(child, False)
    # #                             self.deactivated_prims.add(child_path)
    #                 else:
    #                     # Recursively traverse children of allowed prims
    #                     self.deactivate_children(child_path, keep_active_set)
    def deactivate_children(self, prim, keep_active_set):
        """
        Optimized hierarchical deactivation with parent tracking
        """
        if not prim:
            carb.log_info("Starting with invalid prim")
            return

        #prim = self.stage.GetPrimAtPath(start_prim_path)
        if not prim.IsValid() or not prim.IsActive():
            return

        # Use prim range for bulk processing
        for child in prim.GetAllChildren():
            child_path = child.GetPath()
            str_path = str(child_path)

            if child.GetTypeName() == "Mesh" or "Looks" in str_path:
                continue

            if "mesh_D_Solid" in str_path:  # not ideal but mesh_D_Solid is not included in the attributes list.
                continue

            if str_path not in keep_active_set: # yesy
                if child.IsActive():
                    child.GetAttribute("visibility").Set("invisible")
                    self.deactivated_prims.add(child)
            else:
                # Only recurse into prims that need deeper inspection
                self.deactivate_children(child, keep_active_set)


    #      for path in self.deactivated_prims:
        #          prim = self.stage.GetPrimAtPath(path)
        #          if prim.IsValid():
        #              self.change_state(prim) # default true!
        #      self.deactivated_prims = set()

    def restore_visibility(self):
        """Batched reactivation of parent prims"""
        start = time.time()
        carb.log_info(f"Restoring Visibility ...{start}")  # Debug log
        if not self.deactivated_prims or not self.dirty:
            return

        #imageable_prims = [UsdGeom.Imageable(prim) for prim in self.deactivated_prims if prim.IsValid()]


        #session_layer = self.stage.GetSessionLayer()  # Apply changes to session layer

        # with Usd.EditContext(self.stage, session_layer):  # Optimize writes
        #     # Batch reactivation in single transaction
        # with Sdf.ChangeBlock():
        # #    # self.begin_batch()
        #     for prim in self.deactivated_prims:
        #         prim.GetAttribute("visibility").Set("inherited")

        self.stage.GetRootLayer().subLayerPaths.remove(self.session_layer.identifier)




        finish = time.time()
        carb.log_info(f"Restored Visibility ...{finish} elapsed time is: {finish - start} ")  # Debug log

        carb.log_info(f"Size of the deactivated prims is : {len(self.deactivated_prims)}")
        self.deactivated_prims.clear()
        self.dirty = False # restored!


    def activatePrimsOnly(self, start_path, keep_active_paths):
        """
        Start traversal from start_path, deactivating children not in keep_active_paths.
        """
        start = time.time()
        carb.log_info(f"Activation Visibility ...{start}")  # Debug log
       # keep_active_set = set(keep_active_paths)

        # Get the viewport interface
       # viewport = omni.kit.viewport.utility.get_active_viewport()

        # Disable auto-refresh to suspend redraws
       # viewport.updates_enabled = False

       # session_layer = self.stage.GetSessionLayer()  # Apply changes to session layer

       # viewport = omni.kit.viewport.utility.get_active_viewport()
       # viewport.set_active(False)  # Disable UI updates
        # make sure current deactivated prims have been reactivated.

       # with Usd.EditContext(self.stage, session_layer):  # Optimize writes

        self.session_layer = Sdf.Layer.CreateAnonymous("visablity_overrides")
        self.stage.GetRootLayer().subLayerPaths.append(self.session_layer.identifier)
        self.stage.SetEditTarget(Usd.EditTarget(self.session_layer))
        prim = self.stage.GetPrimAtPath(start_path)

           # self.begin_batch()
        with Sdf.ChangeBlock():
                # Start traversal from the specified prim
            self.deactivate_children(prim, keep_active_paths)
          #  self.end_batch()
        # self.stage.GetRootLayer().subLayerPaths.append(session_layer.identifer)
        # Re-enable auto-refresh once the batch update is complete
      #  viewport.updates_enabled = True
      #  viewport.set_active(True)  # Re-enable UI updates

        # stage.GetRootLayer().subLayerPaths.remove(session_layer.identifier)
        self.dirty = True # made changes
        finish = time.time()
        carb.log_info(f"Finished Activation ...{finish} elapsed time is: {finish - start} ")  # Debug log



    def set_visibility(self, prim, visible):

        UsdGeom.Imageable(prim).GetVisibilityAttr().Set(visibility)
        #prim.visibility.Set(visible)
        ## slower!
        #omni.kit.commands.execute("ChangeProperty", prop_path = prim.GetPath().AppendProperty("visibility"), value = visibility, prev=None)
