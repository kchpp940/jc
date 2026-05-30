"""Runtime-safe parser and option views for jc.

Used by shell_completions and other runtime modules.  Contains only
pure data views derived from installed jc modules — no dependency on
the repository layout or file-system structure of the source repo.
"""

from typing import List, Dict

from .cli_data import long_options_map
from .lib import all_parser_info

ABOUT_OPTIONS: List[str] = ['--about', '-a']
ABOUT_MOD_OPTIONS: List[str] = [
    '--pretty', '-p', '--yaml-out', '-y', '--monochrome', '-m',
    '--force-color', '-C',
]
HELP_OPTIONS: List[str] = ['--help', '-h']
SPECIAL_OPTIONS: List[str] = [
    '--version', '-v', '--bash-comp', '-B', '--zsh-comp', '-Z',
]


def get_jc_info() -> dict:
    from .cli import JcCli
    return JcCli.about_jc()


def get_parsers(
    show_hidden: bool = False,
    show_deprecated: bool = False,
) -> List[dict]:
    return all_parser_info(
        show_hidden=show_hidden,
        show_deprecated=show_deprecated,
    )


def is_parser_module(mod_path: str) -> bool:
    return "jc.parsers." in mod_path


def is_universal_module(mod_path: str) -> bool:
    return "universal" in mod_path


def is_standard_parser_module(mod_path: str) -> bool:
    return is_parser_module(mod_path) and not is_universal_module(mod_path)


def get_parser_names(
    show_hidden: bool = False,
    show_deprecated: bool = False,
) -> List[str]:
    return [
        p["name"]
        for p in get_parsers(
            show_hidden=show_hidden,
            show_deprecated=show_deprecated,
        )
    ]


def get_magic_commands() -> List[str]:
    """Return unique first words of all magic commands from parsers."""
    command_list: List[str] = []
    for cmd in get_parsers():
        if 'magic_commands' in cmd:
            command_list.extend(cmd['magic_commands'])

    return sorted(list(set([i.split()[0] for i in command_list])))


def get_all_options() -> List[str]:
    """Return all CLI options (long and short forms) from long_options_map."""
    options_list: List[str] = []
    for opt in long_options_map:
        options_list.append(opt)
        options_list.append('-' + long_options_map[opt][0])

    return options_list


def get_completion_parsers() -> List[str]:
    """Return parser argument names for shell completion (includes hidden)."""
    p_list: List[str] = []
    for cmd in get_parsers(show_hidden=True):
        if 'argument' in cmd:
            p_list.append(cmd['argument'])

    return p_list


def get_completion_parser_descriptions() -> List[str]:
    """Return parser 'argument:description' strings for zsh completion."""
    pd_list: List[str] = []
    for p in get_parsers(show_hidden=True):
        if 'description' in p:
            pd_list.append(f"'{p['argument']}:{p['description']}'")

    return pd_list


def get_zsh_command_descriptions(command_list: List[str]) -> List[str]:
    """Return command descriptions formatted for zsh completion."""
    zsh_commands: List[str] = []
    for cmd in command_list:
        zsh_commands.append(
            f"""'{cmd}:run "{cmd}" command with magic syntax.'"""
        )

    return zsh_commands


def get_option_descriptions(opt_list: List[str]) -> List[str]:
    """Return 'option:description' strings for the given option list."""
    opt_desc_list: List[str] = []

    for item in opt_list:
        if item in long_options_map:
            opt_desc_list.append(f"'{item}:{long_options_map[item][1]}'")
            continue

        for k, v in long_options_map.items():
            if item[1:] == v[0]:
                opt_desc_list.append(f"'{item}:{v[1]}'")
                continue

    return opt_desc_list


def get_filtered_options() -> List[str]:
    """Return all options with special/about/help options removed."""
    opts = get_all_options()
    for s_option in SPECIAL_OPTIONS:
        opts.remove(s_option)
    for a_option in ABOUT_OPTIONS:
        opts.remove(a_option)
    for h_option in HELP_OPTIONS:
        opts.remove(h_option)
    return opts


def get_release_metadata() -> Dict[str, str]:
    """Return a flat dict of release metadata fields."""
    from .cli import JcCli
    info = JcCli.about_jc()
    return {
        'name': info.get('name', 'jc'),
        'version': info.get('version', 'unknown'),
        'description': info.get('description', ''),
        'author': info.get('author', ''),
        'author_email': info.get('author_email', ''),
        'website': info.get('website', ''),
        'copyright': info.get('copyright', ''),
        'license': info.get('license', ''),
    }
