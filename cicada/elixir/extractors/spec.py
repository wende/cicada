"""
Type spec extraction logic.
"""

from cicada.utils import extract_text_from_node

from .common import _find_attribute_recursive


def extract_specs(node, source_code: bytes) -> dict:
    """Extract all @spec attributes from a module body."""
    specs = {}
    _find_attribute_recursive(node, source_code, specs, "spec", _parse_spec)
    return specs


def _parse_spec(spec_node, source_code: bytes) -> dict | None:
    """Parse a @spec attribute to extract function name, arity, parameter types, and return type."""
    # @spec is represented as: spec(function_signature)
    # We need to find the arguments node and parse the typespec

    for child in spec_node.children:
        if child.type == "arguments":
            # The typespec is in the arguments
            for arg in child.children:
                if arg.type == "binary_operator":
                    # This is the :: operator separating params from return type
                    # Left side has the function call with params
                    # Right side has the return type
                    func_call = None
                    return_type = None
                    found_call = False

                    for op_child in arg.children:
                        if op_child.type == "call":
                            func_call = op_child
                            found_call = True
                        elif found_call and op_child.type not in ["::", "operator"]:
                            # This is the return type node (after :: operator)
                            return_type = extract_text_from_node(op_child, source_code)

                    if func_call:
                        func_name = None
                        param_types = []

                        for fc_child in func_call.children:
                            if fc_child.type == "identifier":
                                func_name = extract_text_from_node(fc_child, source_code)
                            elif fc_child.type == "arguments":
                                param_types = _extract_param_types(fc_child, source_code)

                        if func_name:
                            return {
                                "name": func_name,
                                "arity": len(param_types),
                                "param_types": param_types,
                                "return_type": return_type,
                            }

    return None


def _extract_param_types(params_node, source_code: bytes) -> list[str]:
    """Extract parameter type strings from @spec arguments."""
    param_types = []

    for child in params_node.children:
        if child.type in [",", "(", ")", "[", "]"]:
            continue

        # Get the type as a string
        type_str = extract_text_from_node(child, source_code)
        param_types.append(type_str)

    return param_types


def match_specs_to_functions(functions: list, specs: dict) -> list:
    """Match specs with functions and add type information to function args and return type."""
    for func in functions:
        key = f"{func['name']}/{func['arity']}"
        if key in specs:
            spec = specs[key]
            # Add types to arguments
            if "args" in func and "param_types" in spec:
                # Create args_with_types list
                args_with_types = []
                for i, arg_name in enumerate(func["args"]):
                    if i < len(spec["param_types"]):
                        args_with_types.append({"name": arg_name, "type": spec["param_types"][i]})
                    else:
                        args_with_types.append({"name": arg_name, "type": None})
                func["args_with_types"] = args_with_types

            # Add return type from spec
            if "return_type" in spec and spec["return_type"]:
                func["return_type"] = spec["return_type"]

    return functions
