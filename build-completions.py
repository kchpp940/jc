#!/usr/bin/env python3
# build Bash and Zsh completion scripts and add to the completions folder
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = SCRIPT_DIR
sys.path.insert(0, PROJECT_ROOT)

from jc.shell_completions import bash_completion, zsh_completion

COMPLETIONS_DIR = os.path.join(PROJECT_ROOT, 'completions')
BASH_COMPLETION_FILE = os.path.join(COMPLETIONS_DIR, 'jc_bash_completion.sh')
ZSH_COMPLETION_FILE = os.path.join(COMPLETIONS_DIR, 'jc_zsh_completion.sh')

os.makedirs(COMPLETIONS_DIR, exist_ok=True)

with open(BASH_COMPLETION_FILE, 'w') as f:
    print(bash_completion(), file=f)

with open(ZSH_COMPLETION_FILE, 'w') as f:
    print(zsh_completion(), file=f)
