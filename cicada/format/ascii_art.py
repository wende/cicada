"""ASCII art and banner generation for Cicada CLI."""

from .colors import CYAN, RESET, YELLOW


def generate_gradient_ascii_art():
    """Generate cicada ASCII art with gradient colors from #E5C890 to #D17958."""
    start_hex = "E5C890"
    end_hex = "D17958"

    # Parse hex colors to RGB
    start_rgb = tuple(int(start_hex[i : i + 2], 16) for i in (0, 2, 4))
    end_rgb = tuple(int(end_hex[i : i + 2], 16) for i in (0, 2, 4))

    # ASCII art lines - explicitly defined to preserve all leading spaces
    lines = [
        '       :.,                             . _.: "',
        "      > =.t@_.      .          .     ._ j@F:++<",
        "      .a??_'dB_ a_   . > \" < .    _: _Ba _??p",
        '       ` \'_\'--m."=o.. , @|D,, ..=+".&--",,.',
        "         `.=mm=~\"'_.  .+===+.    \"'~=mm=",
        "            ..-_. '-.  g_._g  .-' .  .",
        "               '.\" ,   mgggm,   , \".'",
        '                    /! "BBB"  !\\',
        "                   /   " + "'" + '"""' + "'    \\",
        '                         "',
    ]

    num_lines = len(lines)
    result_lines = []

    for i, line in enumerate(lines):
        # Calculate interpolation factor (0 to 1)
        t = i / (num_lines - 1) if num_lines > 1 else 0

        # Interpolate RGB values
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * t)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * t)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * t)

        # Create ANSI color code for this line
        color_code = f"\033[38;2;{r};{g};{b}m"
        # Cast to str to satisfy type checker's LiteralString requirement
        colored_line: str = str(color_code + line + "\033[0m")
        result_lines.append(colored_line)  # type: ignore[arg-type]

    return "\n" + "\n".join(result_lines) + "\n"


# Pre-generate the ASCII art banner
CICADA_ASCII_ART = generate_gradient_ascii_art()


def get_welcome_banner():
    """Generate complete welcome banner with ASCII art and welcome message."""
    banner = CICADA_ASCII_ART
    banner += f"{CYAN}{'=' * 66}{RESET}\n"
    banner += f"{YELLOW} Welcome to CICADA - Code Intelligence{RESET}\n"
    banner += f"{CYAN}{'=' * 66}{RESET}\n"
    return banner
