"""
Dependency extraction logic (alias, import, require, use).

Author: Cursor(Auto)
"""

from cicada.utils import extract_text_from_node

from .common import _find_nodes_recursive


def extract_aliases(node, source_code: bytes) -> dict:
    """Extract all alias declarations from a module body."""
    aliases = []
    _find_aliases_recursive(node, source_code, aliases)

    result = {}
    for alias in aliases:
        if alias:
            result.update(alias)
    return result


def _parse_alias_call(node, source_code: bytes) -> dict | None:
    """Parse an alias call and return the alias information."""
    target = None
    arguments = None

    for child in node.children:
        if child.type == "identifier":
            target = child
        elif child.type == "arguments":
            arguments = child

    if target and arguments:
        target_text = extract_text_from_node(target, source_code)

        if target_text == "alias":
            # Parse the alias
            alias_info = _parse_alias(arguments, source_code)
            if alias_info:
                # alias_info is a dict of {short_name: full_name}
                return alias_info
    return None


def _find_aliases_recursive(node, source_code: bytes, aliases: list):
    """Recursively find alias declarations."""
    _find_nodes_recursive(node, source_code, aliases, "call", _parse_alias_call)


def _parse_alias(arguments_node, source_code: bytes) -> dict | None:
    """
    Parse an alias declaration.

    Handles:
    - alias MyApp.User -> {User: MyApp.User}
    - alias MyApp.User, as: U -> {U: MyApp.User}
    - alias MyApp.{User, Post} -> {User: MyApp.User, Post: MyApp.Post}
    """
    result = {}

    for arg_child in arguments_node.children:
        # Simple alias: alias MyApp.User
        if arg_child.type == "alias":
            full_name = extract_text_from_node(arg_child, source_code)
            # Get the last part as the short name
            short_name = full_name.split(".")[-1]
            result[short_name] = full_name

        # Alias with tuple: alias MyApp.{User, Post}
        elif arg_child.type == "dot":
            # The dot node contains: alias (module prefix), dot, and tuple
            module_prefix = None
            tuple_node = None

            for dot_child in arg_child.children:
                if dot_child.type == "alias":
                    module_prefix = extract_text_from_node(dot_child, source_code)
                elif dot_child.type == "tuple":
                    tuple_node = dot_child

            if module_prefix and tuple_node:
                # Extract each alias from the tuple
                for tuple_child in tuple_node.children:
                    if tuple_child.type == "alias":
                        short_name = extract_text_from_node(tuple_child, source_code)
                        full_name = f"{module_prefix}.{short_name}"
                        result[short_name] = full_name

        # Keyword list for 'as:' option
        elif arg_child.type == "keywords":
            # Find the 'as:' keyword
            for kw_child in arg_child.children:
                if kw_child.type == "pair":
                    key_text = None
                    alias_name = None
                    for pair_child in kw_child.children:
                        if pair_child.type == "keyword":
                            # Get keyword text (e.g., "as:")
                            key_text = extract_text_from_node(pair_child, source_code)
                        elif pair_child.type == "alias":
                            alias_name = extract_text_from_node(pair_child, source_code)

                    # If we found 'as:', update the result to use custom name
                    if key_text and "as" in key_text and alias_name:
                        # Get the full module name from previous arg
                        for prev_arg in arguments_node.children:
                            if prev_arg.type == "alias":
                                full_name = extract_text_from_node(prev_arg, source_code)
                                # Remove the default short name and add custom one
                                result.clear()
                                result[alias_name] = full_name
                                break

    return result if result else None


def extract_imports(node, source_code: bytes) -> list:
    """Extract all import declarations from a module body."""

    imports = []

    _find_declarations_recursive(node, source_code, imports, "import")

    return imports


def _parse_declaration_call(node, source_code: bytes, declaration_name: str) -> str | None:
    """Parse a declaration call and return the module name."""
    target = None
    arguments = None

    for child in node.children:
        if child.type == "identifier":
            target = child
        elif child.type == "arguments":
            arguments = child

    if target and arguments:
        target_text = extract_text_from_node(target, source_code)

        if target_text == declaration_name:
            # Parse the declaration
            for arg_child in arguments.children:
                if arg_child.type == "alias":
                    return extract_text_from_node(arg_child, source_code)
    return None


def _find_declarations_recursive(
    node, source_code: bytes, declarations: list, declaration_name: str
):
    """Recursively find declarations."""
    _find_nodes_recursive(
        node,
        source_code,
        declarations,
        "call",
        lambda n, s: _parse_declaration_call(n, s, declaration_name),
    )


def extract_requires(node, source_code: bytes) -> list:
    """Extract all require declarations from a module body."""

    requires = []

    _find_declarations_recursive(node, source_code, requires, "require")

    return requires


def extract_uses(node, source_code: bytes) -> list:
    """Extract all use declarations from a module body."""

    uses = []

    _find_declarations_recursive(node, source_code, uses, "use")

    return uses


def extract_behaviours(node, source_code: bytes) -> list:
    """Extract all @behaviour declarations from a module body."""
    behaviours = []
    _find_behaviours_recursive(node, source_code, behaviours)
    return behaviours


def _parse_behaviour_call(node, source_code: bytes) -> str | None:
    """Parse a behaviour call and return the module name."""
    # Check if this is an @ operator with behaviour
    is_at_operator = False
    behaviour_call = None

    for child in node.children:
        if child.type == "@":
            is_at_operator = True
        elif child.type == "call" and is_at_operator:
            behaviour_call = child
            break

    if behaviour_call:
        # Check if the call is "behaviour"
        identifier_text = None
        arguments_node = None

        for child in behaviour_call.children:
            if child.type == "identifier":
                identifier_text = extract_text_from_node(child, source_code)
            elif child.type == "arguments":
                arguments_node = child

        if identifier_text == "behaviour" and arguments_node:
            # Extract the behaviour module name
            for arg_child in arguments_node.children:
                if arg_child.type == "alias":
                    # @behaviour ModuleName
                    return extract_text_from_node(arg_child, source_code)
                elif arg_child.type == "atom":
                    # @behaviour :module_name
                    atom_text = extract_text_from_node(arg_child, source_code)
                    # Remove leading colon and convert to module format if needed
                    return atom_text.lstrip(":")
    return None


def _find_behaviours_recursive(node, source_code: bytes, behaviours: list):
    """Recursively find @behaviour declarations."""
    _find_nodes_recursive(node, source_code, behaviours, "unary_operator", _parse_behaviour_call)
