"""jc - JSON Convert shell_completions module"""

from string import Template
from typing import Optional, List, Union
from .cli_data import long_options_map
from .lib import ParserList, ParserInfoType


bash_template = Template('''\
_jc()
{
    local cur prev words cword jc_commands jc_parsers jc_options \\
          jc_about_options jc_about_mod_options jc_help_options jc_special_options \\
          jc_parser_subcmd jc_filter_options jc_filter_value_options

    jc_commands=(${bash_commands})
    jc_parsers=(${bash_parsers})
    jc_options=(${bash_options})
    jc_about_options=(${bash_about_options})
    jc_about_mod_options=(${bash_about_mod_options})
    jc_help_options=(${bash_help_options})
    jc_special_options=(${bash_special_options})
    jc_parser_subcmd=(${bash_parser_subcmd})
    jc_filter_options=(${bash_filter_options})
    jc_filter_value_options=(${bash_filter_value_options})

    COMPREPLY=()
    _get_comp_words_by_ref cur prev words cword

    # if 'parsers' subcommand is found, enter parser discovery completion mode
    for i in "$${words[@]::$${#words[@]}-1}"; do
        if [[ "$${i}" == "parsers" ]]; then
            # --filter-category values
            if [[ "$${prev}" == "--filter-category" ]]; then
                COMPREPLY=( $$( compgen -W "${bash_category_values}" -- "$${cur}" ) )
                return 0
            fi
            # --filter-platform values
            if [[ "$${prev}" == "--filter-platform" ]]; then
                COMPREPLY=( $$( compgen -W "${bash_platform_values}" -- "$${cur}" ) )
                return 0
            fi
            # --parser-format values
            if [[ "$${prev}" == "--parser-format" ]]; then
                COMPREPLY=( $$( compgen -W "text json yaml" -- "$${cur}" ) )
                return 0
            fi
            # --filter-name value (free text, no completion)
            if [[ "$${prev}" == "--filter-name" ]]; then
                return 0
            fi
            # complete filter options and format
            COMPREPLY=( $$( compgen -W "$${jc_filter_options[*]} $${jc_filter_value_options[*]} --parser-format --pretty" -- "$${cur}" ) )
            return 0
        fi
    done

    # if jc_about_options are found anywhere in the line, then only complete from jc_about_mod_options
    for i in "$${words[@]::$${#words[@]}-1}"; do
        if [[ " $${jc_about_options[*]} " =~ " $${i} " ]]; then
            COMPREPLY=( $$( compgen -W "$${jc_about_mod_options[*]}" \\
            -- "$${cur}" ) )
            return 0
        fi
    done

    # if jc_help_options and a parser are found anywhere in the line, then no more completions
    if
        (
            for i in "$${words[@]::$${#words[@]}-1}"; do
                if [[ " $${jc_help_options[*]} " =~ " $${i} " ]]; then
                    return 0
                fi
            done
            return 1
        ) && (
            for i in "$${words[@]::$${#words[@]}-1}"; do
                if [[ " $${jc_parsers[*]} " =~ " $${i} " ]]; then
                    return 0
                fi
            done
            return 1
        ); then
        return 0
    fi

    # if jc_help_options are found anywhere in the line, then only complete with parsers
    for i in "$${words[@]::$${#words[@]}-1}"; do
        if [[ " $${jc_help_options[*]} " =~ " $${i} " ]]; then
            COMPREPLY=( $$( compgen -W "$${jc_parsers[*]}" \\
            -- "$${cur}" ) )
            return 0
        fi
    done

    # if special options are found anywhere in the line, then no more completions
    for i in "$${words[@]::$${#words[@]}-1}"; do
        if [[ " $${jc_special_options[*]} " =~ " $${i} " ]]; then
            return 0
        fi
    done

    # if magic command is found anywhere in the line, use called command's autocompletion
    for i in "$${words[@]::$${#words[@]}-1}"; do
        if [[ " $${jc_commands[*]} " =~ " $${i} " ]]; then
            _command
            return 0
        fi
    done

    # if "/pr[oc]" (magic for Procfile parsers) is in the current word, complete with files/directories in the path
    if [[ "$${cur}" =~ "/pr" ]]; then
        _filedir
        return 0
    fi

    # if a parser arg is found anywhere in the line, only show options and help options
    for i in "$${words[@]::$${#words[@]}-1}"; do
        if [[ " $${jc_parsers[*]} " =~ " $${i} " ]]; then
            COMPREPLY=( $$( compgen -W "$${jc_options[*]} $${jc_help_options[*]}" \\
            -- "$${cur}" ) )
            return 0
        fi
    done

    # default completion (includes 'parsers' subcommand)
    COMPREPLY=( $$( compgen -W "$${jc_options[*]} $${jc_about_options[*]} $${jc_help_options[*]} $${jc_special_options[*]} $${jc_parsers[*]} $${jc_commands[*]} $${jc_parser_subcmd[*]}" \\
        -- "$${cur}" ) )
} &&
complete -F _jc jc
''')


zsh_template = Template('''\
#compdef jc

_jc() {
    local -a jc_commands jc_commands_describe \\
             jc_parsers jc_parsers_describe \\
             jc_options jc_options_describe \\
             jc_about_options jc_about_options_describe \\
             jc_about_mod_options jc_about_mod_options_describe \\
             jc_help_options jc_help_options_describe \\
             jc_special_options jc_special_options_describe \\
             jc_parser_subcmd jc_parser_subcmd_describe \\
             jc_filter_options jc_filter_options_describe \\
             jc_filter_value_options jc_filter_value_options_describe

    jc_commands=(${zsh_commands})
    jc_commands_describe=(
        ${zsh_commands_describe}
    )
    jc_parsers=(${zsh_parsers})
    jc_parsers_describe=(
        ${zsh_parsers_describe}
    )
    jc_options=(${zsh_options})
    jc_options_describe=(
        ${zsh_options_describe}
    )
    jc_about_options=(${zsh_about_options})
    jc_about_options_describe=(
        ${zsh_about_options_describe}
    )
    jc_about_mod_options=(${zsh_about_mod_options})
    jc_about_mod_options_describe=(
        ${zsh_about_mod_options_describe}
    )
    jc_help_options=(${zsh_help_options})
    jc_help_options_describe=(
        ${zsh_help_options_describe}
    )
    jc_special_options=(${zsh_special_options})
    jc_special_options_describe=(
        ${zsh_special_options_describe}
    )
    jc_parser_subcmd=('parsers')
    jc_parser_subcmd_describe=(
        'parsers:list and filter available parsers'
    )
    jc_filter_options=(--filter-streaming --filter-no-streaming --filter-slurpable --filter-no-slurpable --filter-plugin --filter-no-plugin --list-parsers)
    jc_filter_options_describe=(
        '--filter-streaming:filter for streaming parsers only'
        '--filter-no-streaming:filter for non-streaming parsers only'
        '--filter-slurpable:filter for slurpable parsers only'
        '--filter-no-slurpable:filter for non-slurpable parsers only'
        '--filter-plugin:filter for local plugin parsers only'
        '--filter-no-plugin:filter for built-in parsers only'
        '--list-parsers:list available parsers'
    )
    jc_filter_value_options=(--filter-category --filter-platform --filter-name --parser-format)
    jc_filter_value_options_describe=(
        '--filter-category:filter by category tags'
        '--filter-platform:filter by compatible platform'
        '--filter-name:filter by name substring'
        '--parser-format:output format: text, json, yaml'
    )

    # if 'parsers' subcommand is found, enter parser discovery completion mode
    for i in $${words:0:-1}; do
        if [[ "$${i}" == "parsers" ]]; then
            case "$${words[-1]}" in
                --filter-category)
                    _describe 'categories' '(${zsh_category_values_describe})'
                    return 0
                    ;;
                --filter-platform)
                    _describe 'platforms' '(${zsh_platform_values_describe})'
                    return 0
                    ;;
                --parser-format)
                    _describe 'formats' '(text:human-readable text json:JSON output yaml:YAML output)'
                    return 0
                    ;;
                --filter-name)
                    return 0
                    ;;
            esac
            _describe 'filter options' jc_filter_options_describe -- jc_filter_value_options_describe
            return 0
        fi
    done

    # if jc_about_options are found anywhere in the line, then only complete from jc_about_mod_options
    for i in $${words:0:-1}; do
        if (( $$jc_about_options[(Ie)$${i}] )); then
            _describe 'commands' jc_about_mod_options_describe
            return 0
        fi
    done

    # if jc_help_options and a parser are found anywhere in the line, then no more completions
     if
        (
            for i in $${words:0:-1}; do
                if (( $$jc_help_options[(Ie)$${i}] )); then
                    return 0
                fi
            done
            return 1
        ) && (
            for i in $${words:0:-1}; do
                if (( $$jc_parsers[(Ie)$${i}] )); then
                    return 0
                fi
            done
            return 1
        ); then
        return 0
    fi

    # if jc_help_options are found anywhere in the line, then only complete with parsers
    for i in $${words:0:-1}; do
        if (( $$jc_help_options[(Ie)$${i}] )); then
            _describe 'commands' jc_parsers_describe
            return 0
        fi
    done

    # if special options are found anywhere in the line, then no more completions
    for i in $${words:0:-1}; do
        if (( $$jc_special_options[(Ie)$${i}] )); then
            return 0
        fi
    done

    # if magic command is found anywhere in the line, use called command's autocompletion
    for i in $${words:0:-1}; do
        if (( $$jc_commands[(Ie)$${i}] )); then
            # hack to remove options between jc and the magic command
            shift $$(( $${#words} - 2 )) words
            words[1,0]=(jc)
            CURRENT=$${#words}

            # run the magic command's completions
            _arguments '*::arguments:_normal'
            return 0
        fi
    done

    # if "/pr[oc]" (magic for Procfile parsers) is in the current word, complete with files/directories in the path
    if [[ "$${words[-1]}" =~ "/pr" ]]; then
        # run files completion
        _files
        return 0
    fi

    # if a parser arg is found anywhere in the line, only show options and help options
    for i in $${words:0:-1}; do
        if (( $$jc_parsers[(Ie)$${i}] )); then
            _describe 'commands' jc_options_describe -- jc_help_options_describe
            return 0
        fi
    done

    # default completion (includes 'parsers' subcommand)
    _describe 'commands' jc_options_describe -- jc_about_options_describe -- jc_help_options_describe -- jc_special_options_describe -- jc_parsers_describe -- jc_commands_describe -- jc_parser_subcmd_describe
}

_jc
''')

about_options = ['--about', '-a']
about_mod_options = ['--pretty', '-p', '--yaml-out', '-y', '--monochrome', '-m', '--force-color', '-C']
help_options = ['--help', '-h']
special_options = ['--version', '-v', '--bash-comp', '-B', '--zsh-comp', '-Z']

CATEGORY_VALUES = ['command', 'generic', 'standard', 'file', 'string', 'binary', 'slurpable']
PLATFORM_VALUES = ['linux', 'darwin', 'win32', 'cygwin', 'aix', 'freebsd']


def get_parser_list(
    show_hidden: bool = True,
    category: Optional[Union[str, List[str]]] = None,
    platform: Optional[Union[str, List[str]]] = None,
    streaming: Optional[bool] = None,
    slurpable: Optional[bool] = None,
    plugin: Optional[bool] = None,
    name: Optional[str] = None
) -> ParserList:
    """
    Unified parser discovery for shell completions.
    Uses the same ParserList.discover() as CLI and Python API.
    """
    return ParserList.discover(
        category=category,
        platform=platform,
        streaming=streaming,
        slurpable=slurpable,
        plugin=plugin,
        name=name,
        show_hidden=show_hidden,
        show_deprecated=False
    )


def get_commands(parser_list: Optional[ParserList] = None):
    if parser_list is None:
        parser_list = get_parser_list()

    return parser_list.magic_commands()


def get_options():
    options_list = []
    for opt in long_options_map:
        options_list.append(opt)
        short_opt = long_options_map[opt][0]
        if short_opt:
            options_list.append('-' + short_opt)

    return options_list


def get_parsers(parser_list: Optional[ParserList] = None):
    if parser_list is None:
        parser_list = get_parser_list()

    return parser_list.arguments()


def get_parsers_descriptions(parser_list: Optional[ParserList] = None):
    if parser_list is None:
        parser_list = get_parser_list()

    return parser_list.descriptions()


def get_zsh_command_descriptions(command_list):
    zsh_commands = []
    for cmd in command_list:
        zsh_commands.append(f"""'{cmd}:run "{cmd}" command with magic syntax.'""")

    return zsh_commands


def get_descriptions(opt_list):
    """Return a list of options:description items."""
    opt_desc_list = []

    for item in opt_list:
        if item in long_options_map:
            opt_desc_list.append(f"'{item}:{long_options_map[item][1]}'")
            continue

        for k, v in long_options_map.items():
            if v[0] and item[1:] == v[0]:
                opt_desc_list.append(f"'{item}:{v[1]}'")
                continue

    return opt_desc_list


def _get_filter_options():
    """Return filter flag options (no value needed)."""
    return [
        '--filter-streaming', '--filter-no-streaming',
        '--filter-slurpable', '--filter-no-slurpable',
        '--filter-plugin', '--filter-no-plugin',
        '--list-parsers'
    ]


def _get_filter_value_options():
    """Return filter options that require a value."""
    return [
        '--filter-category', '--filter-platform',
        '--filter-name', '--parser-format'
    ]


def bash_completion():
    parsers_str = ' '.join(get_parsers())
    opts_no_special = get_options()

    for s_option in special_options:
        opts_no_special.remove(s_option)

    for a_option in about_options:
        opts_no_special.remove(a_option)

    for h_option in help_options:
        opts_no_special.remove(h_option)

    options_str = ' '.join(opts_no_special)
    about_options_str = ' '.join(about_options)
    about_mod_options_str = ' '.join(about_mod_options)
    help_options_str = ' '.join(help_options)
    special_options_str = ' '.join(special_options)
    commands_str = ' '.join(get_commands())
    filter_options_str = ' '.join(_get_filter_options())
    filter_value_options_str = ' '.join(_get_filter_value_options())
    category_values_str = ' '.join(CATEGORY_VALUES)
    platform_values_str = ' '.join(PLATFORM_VALUES)

    return bash_template.substitute(
        bash_parsers=parsers_str,
        bash_special_options=special_options_str,
        bash_about_options=about_options_str,
        bash_about_mod_options=about_mod_options_str,
        bash_help_options=help_options_str,
        bash_options=options_str,
        bash_commands=commands_str,
        bash_parser_subcmd='parsers',
        bash_filter_options=filter_options_str,
        bash_filter_value_options=filter_value_options_str,
        bash_category_values=category_values_str,
        bash_platform_values=platform_values_str
    )


def zsh_completion():
    parsers_str = ' '.join(get_parsers())
    parsers_describe = '\n        '.join(get_parsers_descriptions())
    opts_no_special = get_options()

    for s_option in special_options:
        opts_no_special.remove(s_option)

    for a_option in about_options:
        opts_no_special.remove(a_option)

    for h_option in help_options:
        opts_no_special.remove(h_option)

    options_str = ' '.join(opts_no_special)
    options_describe = '\n        '.join(get_descriptions(opts_no_special))
    about_options_str = ' '.join(about_options)
    about_options_describe = '\n        '.join(get_descriptions(about_options))
    about_mod_options_str = ' '.join(about_mod_options)
    about_mod_options_describe = '\n        '.join(get_descriptions(about_mod_options))
    help_options_str = ' '.join(help_options)
    help_options_describe = '\n        '.join(get_descriptions(help_options))
    special_options_str = ' '.join(special_options)
    special_options_describe = '\n        '.join(get_descriptions(special_options))
    commands_str = ' '.join(get_commands())
    commands_describe = '\n        '.join(get_zsh_command_descriptions(get_commands()))

    category_describe = '\n        '.join(
        f"'{c}:{c} parser category'" for c in CATEGORY_VALUES
    )
    platform_describe = '\n        '.join(
        f"'{p}:{p} platform'" for p in PLATFORM_VALUES
    )

    return zsh_template.substitute(
        zsh_parsers=parsers_str,
        zsh_parsers_describe=parsers_describe,
        zsh_special_options=special_options_str,
        zsh_special_options_describe=special_options_describe,
        zsh_about_options=about_options_str,
        zsh_about_options_describe=about_options_describe,
        zsh_about_mod_options=about_mod_options_str,
        zsh_about_mod_options_describe=about_mod_options_describe,
        zsh_help_options=help_options_str,
        zsh_help_options_describe=help_options_describe,
        zsh_options=options_str,
        zsh_options_describe=options_describe,
        zsh_commands=commands_str,
        zsh_commands_describe=commands_describe,
        zsh_category_values_describe=category_describe,
        zsh_platform_values_describe=platform_describe
    )
