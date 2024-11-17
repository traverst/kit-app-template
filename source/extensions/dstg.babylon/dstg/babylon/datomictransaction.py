

## Claude Sonat generated!

from typing import Dict, Any, List
import re
from decimal import Decimal

def parse_property_name(key: str) -> tuple[str, str]:
    """
    Parse a property key into group and name components.
    E.g., 'Material*Ambient.Blue' -> ('Material', 'Ambient.Blue')
    """
    if '*' in key:
        group, name = key.split('*', 1)
        return group, name
    return '', key

def detect_value_type(value: Any) -> str:
    """
    Determine the appropriate Datomic value type for a given Python value.
    Returns one of: 'string', 'int', 'float', 'bool', 'vector', 'entity'
    """
    if isinstance(value, bool):
        return 'bool'
    elif isinstance(value, int):
        return 'int'
    elif isinstance(value, (float, Decimal)):
        return 'float'
    elif isinstance(value, (list, tuple)) and len(value) == 3:
        # Assuming any 3-element sequence is a vector3
        return 'vector'
    elif isinstance(value, dict):
        return 'entity'
    else:
        return 'string'

def create_property_entity(name: str, value: Any, group: str = '') -> Dict:
    """
    Create a property entity with the appropriate value type.
    Includes group as a property if specified.
    """
    value_type = detect_value_type(value)

    property_entity = {
        ':property/name': name,
    }

    # Add group if present
    if group:
        property_entity[':property/group'] = str(group)

    # Add the appropriate value field based on type
    if value_type == 'string':
        property_entity[':property/string-value'] = str(value)
    elif value_type == 'int':
        property_entity[':property/int-value'] = int(value)
    elif value_type == 'float':
        property_entity[':property/float-value'] = float(value)
    elif value_type == 'bool':
        property_entity[':property/bool-value'] = bool(value)
    elif value_type == 'vector':
        property_entity[':property/vector-value'] = [float(x) for x in value]
    elif value_type == 'entity':
        # For nested objects, recursively convert them
        nested_entity = convert_to_datomic_entity(value)
        if nested_entity:  # Only include if the nested entity is not empty
            property_entity[':property/entity-value'] = nested_entity
        else:
            return None

    return property_entity

def convert_to_datomic_entity(data: Dict[str, Any]) -> Dict:
    """
    Convert a Python dictionary into a Datomic entity format.
    Properties maintain their group information as a property attribute.
    Returns None if the entity has no valid properties.
    """
    if not data:
        return None

    # Extract the name/identifier from the key
    key = next(iter(data))  # Get the first (and only) key
    properties_data = data[key]

    if not properties_data:  # Skip if no properties
        return None

    result = {
        ':object/name': key,
        ':object/properties': []
    }

    # Process all properties, maintaining group information
    for prop_key, value in properties_data.items():
        group, name = parse_property_name(prop_key)
        property_entity = create_property_entity(name, value, group)
        if property_entity:  # Only add if property creation was successful
            result[':object/properties'].append(property_entity)

    # Return None if no valid properties were found
    return result if result[':object/properties'] else None

def process_entities(data: Dict[str, Dict[str, Any]]) -> List[Dict]:
    """
    Process multiple entities from a dictionary of entity data.
    Skips empty entities and returns a list of valid Datomic entities.
    """
    datomic_entities = []

    for key, properties in data.items():
        entity_data = {key: properties}
        entity = convert_to_datomic_entity(entity_data)
        if entity:  # Only include non-empty entities
            datomic_entities.append(entity)

    return datomic_entities


## ChatGPT generated!

def dict_to_custom_format(d):
    if isinstance(d, dict):
        elements = []
        for k, v in d.items():
            # Recursive call for nested dictionaries or lists
            formatted_value = dict_to_custom_format(v)
            elements.append(f"{k} {formatted_value}")
        return f"{{{' '.join(elements)}}}"
    elif isinstance(d, list):
        # Format each item in the list
        formatted_list = ' '.join([dict_to_custom_format(item) for item in d])
        return f"[{formatted_list}]"
    elif isinstance(d, str):
        # String values should be quoted
        return f'"{d}"'
    elif isinstance(d, (int, float)):
        # Numerical values are directly added
        return f"{d:.3f}" if isinstance(d, float) else str(d)
    else:
        raise ValueError("Unsupported data type")

result = f"[{dict_to_custom_format(datomic_entities[0])}]"
print(result)
