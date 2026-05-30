"""jc - JSON Convert shell_completions module"""

from string import Template
from ._docgen import (
    get_magic_commands,
    get_all_options,
    get_completion_parsers,
    get_completion_parser_descriptions,
    get_zsh_command_descriptions,
    get_option_descriptions,
    get_filtered_options,
    ABOUT_OPTIONS,
    ABOUT_MOD_OPTIONS,
    HELP_OPTIONS,
    SPECIAL_OPTIONS,
)


bash_template = Template('''\
_jc()
{
    local cur prev words cword jc_commands jc_parsers jc_options \\
          jc_about_options jc_about_mod_options jc_help_options jc_special_options

    jc_commands=(${bash_commands})
    jc_parsers=(${bash_parsers})
    jc_options=(${bash_options})
    jc_about_options=(${bash_about_options})
    jc_about_mod_options=(${bash_about_mod_options})
    jc_help_options=(${bash_help_options})
    jc_special_options=(${bash_special_options})

    COMPREPLY=()
    _get_comp_words_by_ref cur prev words cword

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

    # default completion
    COMPREPLY=( $$( compgen -W "$${jc_options[*]} $${jc_about_options[*]} $${jc_help_options[*]} $${jc_special_options[*]} $${jc_parsers[*]} $${jc_commands[*]}" \\
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
             jc_special_options jc_special_options_describe

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

    # default completion
    _describe 'commands' jc_options_describe -- jc_about_options_describe -- jc_help_options_describe -- jc_special_options_describe -- jc_parsers_describe -- jc_commands_describe
}

_jc
''')


def bash_completion():
    parsers_str = ' '.join(get_completion_parsers())
    opts_no_special = get_filtered_options()
    options_str = ' '.join(opts_no_special)
    about_options_str = ' '.join(ABOUT_OPTIONS)
    about_mod_options_str = ' '.join(ABOUT_MOD_OPTIONS)
    help_options_str = ' '.join(HELP_OPTIONS)
    special_options_str = ' '.join(SPECIAL_OPTIONS)
    commands_str = ' '.join(get_magic_commands())
    return bash_template.substitute(
        bash_parsers=parsers_str,
        bash_special_options=special_options_str,
        bash_about_options=about_options_str,
        bash_about_mod_options=about_mod_options_str,
        bash_help_options=help_options_str,
        bash_options=options_str,
        bash_commands=commands_str
    )


def zsh_completion():
    parsers_str = ' '.join(get_completion_parsers())
    parsers_describe = '\n        '.join(get_completion_parser_descriptions())
    opts_no_special = get_filtered_options()
    options_str = ' '.join(opts_no_special)
    options_describe = '\n        '.join(get_option_descriptions(opts_no_special))
    about_options_str = ' '.join(ABOUT_OPTIONS)
    about_options_describe = '\n        '.join(get_option_descriptions(ABOUT_OPTIONS))
    about_mod_options_str = ' '.join(ABOUT_MOD_OPTIONS)
    about_mod_options_describe = '\n        '.join(get_option_descriptions(ABOUT_MOD_OPTIONS))
    help_options_str = ' '.join(HELP_OPTIONS)
    help_options_describe = '\n        '.join(get_option_descriptions(HELP_OPTIONS))
    special_options_str = ' '.join(SPECIAL_OPTIONS)
    special_options_describe = '\n        '.join(get_option_descriptions(SPECIAL_OPTIONS))
    commands = get_magic_commands()
    commands_str = ' '.join(commands)
    commands_describe = '\n        '.join(get_zsh_command_descriptions(commands))

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
        zsh_commands_describe=commands_describe
    )
