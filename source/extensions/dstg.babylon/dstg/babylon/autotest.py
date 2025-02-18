import numpy as np
import omni.graph.core as og
import omni.graph.core.types as ot



@og.create_node_type
def autonode_dot(vector1: ot.vector3d, vector2: ot.vector3d) -> ot.double:
    return np.dot(vector1,vector2)