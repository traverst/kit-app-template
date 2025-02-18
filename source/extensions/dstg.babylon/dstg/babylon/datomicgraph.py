import omni.graph.core as og
import omni.graph.core.types as ot

class DatalogQueryParser:
    """
    Utility class to parse and process Datalog query components
    """
    @staticmethod
    def parse_find_clauses(find_string: str) -> list:
        """
        Parse find clauses from a comma-separated string
        
        :param find_string: Comma-separated find variables
        :return: List of find clauses
        """
        if not find_string:
            return []
        return [var.strip() for var in find_string.split(',,')]

    @staticmethod
    def parse_where_clauses(where_string: str) -> list:
        """
        Parse where clauses from a comma-separated string
        
        :param where_string: Comma-separated where clauses
        :return: List of where clauses
        """
        if not where_string:
            return []
        
        # Split and clean clauses
        raw_clauses = [clause.strip() for clause in where_string.split(',,')]
        
        # Option to support different clause formats
        parsed_clauses = []
        for clause in raw_clauses:
            # Basic clause parsing 
            # Supports: 
            # - Direct clauses like '[?e :person/name ?name]'
            # - Shorthand like 'e,person/name,name'
            if clause.startswith('['):
                parsed_clauses.append(clause)
            else:
                parts = clause.split(',')
                if len(parts) == 3:
                    parsed_clauses.append(f"[?{parts[0]} :{parts[1]} ?{parts[2]}]")
                else:
                    parsed_clauses.append(clause)
        
        return parsed_clauses

    @staticmethod
    def parse_predicate_clauses(pred_string: str) -> list:
        """
        Parse predicate clauses from a comma-separated string
        
        :param pred_string: Comma-separated predicate clauses
        :return: List of predicate clauses
        """
        if not pred_string:
            return []
        
        raw_clauses = [clause.strip() for clause in pred_string.split(',,')]
        
        parsed_predicates = []
        for clause in raw_clauses:
            # Supports formats like:
            # '>,age,30'
            # '(> ?age 30)'
            if clause.startswith('('):
                parsed_predicates.append(clause)
            else:
                parts = clause.split(',')
                if len(parts) == 3:
                    parsed_predicates.append(f"[({parts[0]} ?{parts[1]} {parts[2]})]")
                else:
                    parsed_predicates.append(clause)
        
        return parsed_predicates

    @staticmethod
    def parse_input_clauses(input_string: str) -> list:
        """
        Parse input clauses from a comma-separated string
        
        :param input_string: Comma-separated input clauses
        :return: List of input clauses
        """
        if not input_string:
            return []
        return [clause.strip() for clause in input_string.split(',,')]

    @staticmethod
    def parse_rule_clauses(rule_string: str) -> list:
        """
        Parse rule clauses from a comma-separated string
        
        :param rule_string: Comma-separated rule clauses
        :return: List of rule clauses
        """
        if not rule_string:
            return []
        return [clause.strip() for clause in rule_string.split(',,')]

    """
    Utility class to parse and process Datalog query components
    """
    @staticmethod
    def parse_array_input(input_array: ot.tokenarray) -> str:
        """
        Parse an array of tokens into a comma-separated string
        
        :param input_array: Array of tokens
        :return: Comma-separated string
        """
        if not input_array or len(input_array) == 0:
            return None
        
        # Convert to comma-separated string, handling potential None values
        return ',,'.join(str(token) for token in input_array if token is not None)

    @staticmethod
    def compose_query(
        find_clauses: ot.tokenarray = None, 
        where_clauses: ot.tokenarray = None, 
        predicate_clauses: ot.tokenarray = None,
        input_clauses: ot.tokenarray = None,
        rule_clauses: ot.tokenarray = None
    ) -> str:
        """
        Compose a complete Datomic Datalog query from input arrays
        
        :return: Complete Datalog query string
        """
        # Convert array inputs to strings
        find_string = DatalogQueryParser.parse_array_input(find_clauses)
        where_string = DatalogQueryParser.parse_array_input(where_clauses)
        predicate_string = DatalogQueryParser.parse_array_input(predicate_clauses)
        input_string = DatalogQueryParser.parse_array_input(input_clauses)
        rule_string = DatalogQueryParser.parse_array_input(rule_clauses)

        # Use existing parsing logic
        find_parsed = DatalogQueryParser.parse_find_clauses(find_string or '')
        where_parsed = DatalogQueryParser.parse_where_clauses(where_string or '')
        predicate_parsed = DatalogQueryParser.parse_predicate_clauses(predicate_string or '')
        input_parsed = DatalogQueryParser.parse_input_clauses(input_string or '')
        rule_parsed = DatalogQueryParser.parse_rule_clauses(rule_string or '')

        # Combine all where and predicate clauses
        all_where_clauses = where_parsed + predicate_parsed

        # Construct query
        query = "["
        
        # Find clause
        if find_parsed:
            query += ":find " + " ".join(find_parsed)
        
        # Input clause
        if input_parsed:
            query += " :in $" + " " + " ".join(input_parsed)
        
        # Where clause
        if all_where_clauses:
            query += " :where " + " ".join(all_where_clauses)
        
        # Rules
        if rule_parsed:
            query += " :rules [" + " ".join(rule_parsed) + "]"
        
        query += "]"
        return query

@og.create_node_type
def datomic_flexible_query(
    find_clauses: ot.tokenarray = None,  # List of find variables
    where_clauses: ot.tokenarray = None,  # Array of where clauses
    predicate_clauses: ot.tokenarray = None,  # Array of predicate clauses
    input_clauses: ot.tokenarray = None,  # Array of input clauses
    rule_clauses: ot.tokenarray = None  # Array of rule clauses
) -> ot.token:
    """
    Flexible Datalog query composition node with support for multiple inputs
    
    Supports connecting multiple nodes to `find_clauses` using `list[ot.token]`.
    """
    return DatalogQueryParser.compose_query(
        find_clauses=find_clauses, 
        where_clauses=where_clauses,
        predicate_clauses=predicate_clauses,
        input_clauses=input_clauses,
        rule_clauses=rule_clauses
    )

# Support Nodes for Specific Query Components
@og.create_node_type
def datomic_find_clause(
    variable: ot.token,  # Variable to find (e.g., '?name')
    prefix: ot.token = None  # Optional prefix for variable
) -> ot.token:
    """
    Create a find clause for Datalog query
    
    :param variable: The variable to find
    :param prefix: Optional prefix to modify the variable
    :return: Formatted find clause
    """
    # If prefix is provided, modify the variable
    if prefix:
        return f"{prefix}{variable}"
    return variable

@og.create_node_type
def datomic_where_clause(
    entity: ot.token,     # Entity variable (e.g., '?e')
    attribute: ot.token,  # Attribute keyword (e.g., ':person/name')
    value: ot.token       # Value variable (e.g., '?name')
) -> ot.token:
    """
    Create a basic where clause for Datalog query
    
    :param entity: Entity variable
    :param attribute: Attribute keyword
    :param value: Value variable
    :return: Formatted where clause
    """
    return f"[{entity} {attribute} {value}]"

@og.create_node_type
def datomic_predicate_clause(
    predicate: ot.token,  # Predicate function (e.g., '>', '<', '=')
    arg1: ot.token,       # First argument
    arg2: ot.token        # Second argument
) -> ot.token:
    """
    Create a predicate clause for Datalog query
    
    :param predicate: Comparison or logic predicate
    :param arg1: First argument
    :param arg2: Second argument
    :return: Formatted predicate clause
    """
    return f"[({predicate} {arg1} {arg2})]"

# Rule Clause Node
@og.create_node_type
def autonode_rule_clause(
    rule_name: ot.token,         # Name of the rule
    rule_variables: ot.token,    # Variables for the rule
    rule_body: ot.token          # Rule body definition
) -> ot.token:
    """
    Create a rule clause for Datalog query
    
    :param rule_name: Name of the rule
    :param rule_variables: Variables involved in the rule
    :param rule_body: Body of the rule definition
    :return: Formatted rule clause
    """
    return f"[{rule_name} {rule_variables} {rule_body}]"

# Input Clause Node
@og.create_node_type
def autonode_input_clause(
    variable: ot.token,  # Input variable
    value: ot.token      # Input value
) -> ot.token:
    """
    Create an input clause for Datalog query
    
    :param variable: Input variable name
    :param value: Input value
    :return: Formatted input clause
    """
    return f"{variable} {value}"

# Optional: Registration Function
def register_datalog_nodes():
    """
    Register all custom Datalog query nodes
    """
    og.register_node(datomic_flexible_query, 'datalog_flexible_query')
    og.register_node(datomic_find_clause, 'datalog_find_clause')
    og.register_node(datomic_where_clause, 'datalog_where_clause')
    og.register_node(datomic_predicate_clause, 'datalog_predicate_clause')