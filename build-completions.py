#!/usr/bin/env python3
# build Bash and Zsh completion scripts and add to the completions folder
from jc.shell_completions import bash_completion, zsh_completion
from _docgen import write_output, COMPLETIONS_DIR

write_output(COMPLETIONS_DIR / 'jc_bash_completion.sh', bash_completion() + '\n')
write_output(COMPLETIONS_DIR / 'jc_zsh_completion.sh', zsh_completion() + '\n')
