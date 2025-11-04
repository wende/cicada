from cicada.utils import extract_text_from_node, is_function_definition_call


def _find_nodes_recursive(node, source_code: bytes, results: list, node_type: str, parse_function):
    """Recursively find nodes of a specific type and parse them."""
    if node.type == node_type:
        result = parse_function(node, source_code)
        if result:
            if isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)

    # Recursively search children, but skip function bodies
    for child in node.children:
        if child.type == "call" and is_function_definition_call(child, source_code):
            continue

        _find_nodes_recursive(child, source_code, results, node_type, parse_function)


def _find_attribute_recursive(
    node, source_code: bytes, attributes: dict, attribute_name: str, parse_function
):
    """Recursively find attribute declarations."""
    # Look for unary_operator nodes (which represent @ attributes)
    if node.type == "unary_operator":
        operator = None
        operand = None

        for child in node.children:
            if child.type == "@":
                operator = child
            elif child.type == "call":
                operand = child

        if operator and operand:
            # Check if this is a doc attribute
            for call_child in operand.children:
                if call_child.type == "identifier":
                    attr_name = extract_text_from_node(call_child, source_code)

                    if attr_name == attribute_name:
                        # Extract the doc definition
                        if attribute_name == "spec":
                            attribute_info = parse_function(operand, source_code)
                        else:
                            attribute_info = parse_function(
                                operand, source_code, node.start_point[0] + 1
                            )
                        if attribute_info:
                            if attribute_name == "doc":
                                attributes[attribute_info["line"]] = attribute_info
                            elif attribute_name == "spec":
                                key = f"{attribute_info['name']}/{attribute_info['arity']}"
                                attributes[key] = attribute_info

    # Recursively search children
    for child in node.children:
        # Don't recurse into nested defmodule or function definitions
        if child.type == "call" and is_function_definition_call(child, source_code):
            continue

        _find_attribute_recursive(child, source_code, attributes, attribute_name, parse_function)
