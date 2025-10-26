"""
Dependency extraction logic (alias, import, require, use).
"""


def extract_aliases(node, source_code: bytes) -> dict:
    """Extract all alias declarations from a module body."""
    aliases = {}
    _find_aliases_recursive(node, source_code, aliases)
    return aliases


def _find_aliases_recursive(node, source_code: bytes, aliases: dict):
    """Recursively find alias declarations."""
    if node.type == "call":
        target = None
        arguments = None

        for child in node.children:
            if child.type == "identifier":
                target = child
            elif child.type == "arguments":
                arguments = child

        if target and arguments:
            target_text = source_code[target.start_byte : target.end_byte].decode(
                "utf-8"
            )

            if target_text == "alias":
                # Parse the alias
                alias_info = _parse_alias(arguments, source_code)
                if alias_info:
                    # alias_info is a dict of {short_name: full_name}
                    aliases.update(alias_info)

    # Recursively search children, but skip function bodies
    for child in node.children:
        if child.type == "call":
            is_function_def = False
            for call_child in child.children:
                if call_child.type == "identifier":
                    target_text = source_code[
                        call_child.start_byte : call_child.end_byte
                    ].decode("utf-8")
                    if target_text in ["def", "defp", "defmodule"]:
                        is_function_def = True
                        break

            if is_function_def:
                continue

        _find_aliases_recursive(child, source_code, aliases)


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
            full_name = source_code[arg_child.start_byte : arg_child.end_byte].decode(
                "utf-8"
            )
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
                    module_prefix = source_code[
                        dot_child.start_byte : dot_child.end_byte
                    ].decode("utf-8")
                elif dot_child.type == "tuple":
                    tuple_node = dot_child

            if module_prefix and tuple_node:
                # Extract each alias from the tuple
                for tuple_child in tuple_node.children:
                    if tuple_child.type == "alias":
                        short_name = source_code[
                            tuple_child.start_byte : tuple_child.end_byte
                        ].decode("utf-8")
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
                            key_text = source_code[
                                pair_child.start_byte : pair_child.end_byte
                            ].decode("utf-8")
                        elif pair_child.type == "alias":
                            alias_name = source_code[
                                pair_child.start_byte : pair_child.end_byte
                            ].decode("utf-8")

                    # If we found 'as:', update the result to use custom name
                    if key_text and "as" in key_text and alias_name:
                        # Get the full module name from previous arg
                        for prev_arg in arguments_node.children:
                            if prev_arg.type == "alias":
                                full_name = source_code[
                                    prev_arg.start_byte : prev_arg.end_byte
                                ].decode("utf-8")
                                # Remove the default short name and add custom one
                                result.clear()
                                result[alias_name] = full_name
                                break

    return result if result else None


def extract_imports(node, source_code: bytes) -> list:
    """Extract all import declarations from a module body."""
    imports = []
    _find_imports_recursive(node, source_code, imports)
    return imports


def _find_imports_recursive(node, source_code: bytes, imports: list):
    """Recursively find import declarations."""
    if node.type == "call":
        target = None
        arguments = None

        for child in node.children:
            if child.type == "identifier":
                target = child
            elif child.type == "arguments":
                arguments = child

        if target and arguments:
            target_text = source_code[target.start_byte : target.end_byte].decode(
                "utf-8"
            )

            if target_text == "import":
                # Parse the import - imports are simpler than aliases
                # import MyModule or import MyModule, only: [func: 1]
                for arg_child in arguments.children:
                    if arg_child.type == "alias":
                        module_name = source_code[
                            arg_child.start_byte : arg_child.end_byte
                        ].decode("utf-8")
                        imports.append(module_name)

    # Recursively search children, but skip function bodies
    for child in node.children:
        if child.type == "call":
            is_function_def = False
            for call_child in child.children:
                if call_child.type == "identifier":
                    target_text = source_code[
                        call_child.start_byte : call_child.end_byte
                    ].decode("utf-8")
                    if target_text in ["def", "defp", "defmodule"]:
                        is_function_def = True
                        break

            if is_function_def:
                continue

        _find_imports_recursive(child, source_code, imports)


def extract_requires(node, source_code: bytes) -> list:
    """Extract all require declarations from a module body."""
    requires = []
    _find_requires_recursive(node, source_code, requires)
    return requires


def _find_requires_recursive(node, source_code: bytes, requires: list):
    """Recursively find require declarations."""
    if node.type == "call":
        target = None
        arguments = None

        for child in node.children:
            if child.type == "identifier":
                target = child
            elif child.type == "arguments":
                arguments = child

        if target and arguments:
            target_text = source_code[target.start_byte : target.end_byte].decode(
                "utf-8"
            )

            if target_text == "require":
                # Parse the require
                for arg_child in arguments.children:
                    if arg_child.type == "alias":
                        module_name = source_code[
                            arg_child.start_byte : arg_child.end_byte
                        ].decode("utf-8")
                        requires.append(module_name)

    # Recursively search children, but skip function bodies
    for child in node.children:
        if child.type == "call":
            is_function_def = False
            for call_child in child.children:
                if call_child.type == "identifier":
                    target_text = source_code[
                        call_child.start_byte : call_child.end_byte
                    ].decode("utf-8")
                    if target_text in ["def", "defp", "defmodule"]:
                        is_function_def = True
                        break

            if is_function_def:
                continue

        _find_requires_recursive(child, source_code, requires)


def extract_uses(node, source_code: bytes) -> list:
    """Extract all use declarations from a module body."""
    uses = []
    _find_uses_recursive(node, source_code, uses)
    return uses


def _find_uses_recursive(node, source_code: bytes, uses: list):
    """Recursively find use declarations."""
    if node.type == "call":
        target = None
        arguments = None

        for child in node.children:
            if child.type == "identifier":
                target = child
            elif child.type == "arguments":
                arguments = child

        if target and arguments:
            target_text = source_code[target.start_byte : target.end_byte].decode(
                "utf-8"
            )

            if target_text == "use":
                # Parse the use
                for arg_child in arguments.children:
                    if arg_child.type == "alias":
                        module_name = source_code[
                            arg_child.start_byte : arg_child.end_byte
                        ].decode("utf-8")
                        uses.append(module_name)

    # Recursively search children, but skip function bodies
    for child in node.children:
        if child.type == "call":
            is_function_def = False
            for call_child in child.children:
                if call_child.type == "identifier":
                    target_text = source_code[
                        call_child.start_byte : call_child.end_byte
                    ].decode("utf-8")
                    if target_text in ["def", "defp", "defmodule"]:
                        is_function_def = True
                        break

            if is_function_def:
                continue

        _find_uses_recursive(child, source_code, uses)
