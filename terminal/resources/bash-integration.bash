# Private Bash integration for Cayman. The application creates this rcfile and
# its session directory (0700). No model-generated text is ever evaluated here.
[[ -r ~/.bashrc ]] && source ~/.bashrc
set -o emacs
__cayman_dir=$CAYMAN_SESSION_DIR
unset CAYMAN_SESSION_DIR
IFS= read -r __cayman_nonce < "$__cayman_dir/nonce"
readonly __cayman_pid=$BASHPID
__cayman_sequence=0
__cayman_emit() {
    [[ $BASHPID == "$__cayman_pid" ]] || return
    local cwd kind=$1 status=$2 text=$3
    cwd=$(builtin pwd -P)
    # Reject oversized records, never silently truncate command or directory data.
    local LC_ALL=C
    if (( ${#cwd} + ${#text} >= 3800 )); then
        # Explicitly invalidate integration; never retain an older snapshot.
        kind=overflow status=0 cwd=/ text=''
    fi
    ((__cayman_sequence+=1))
    builtin printf '%s\0%s\0%s\0%s\0%s\0%s\0' "$__cayman_nonce" "$__cayman_sequence" "$kind" "$status" "$cwd" "$text" > "$__cayman_dir/events"
}
__cayman_prompt() {
    local status=$?
    __cayman_emit prompt "$status" ''
    builtin printf '\033]133;A\007'
}
# Keep user prompt customization; capture status before it changes $?.
if declare -p PROMPT_COMMAND 2>/dev/null | grep -q 'declare -a'; then
    PROMPT_COMMAND=(__cayman_prompt "${PROMPT_COMMAND[@]}")
else
    PROMPT_COMMAND=(__cayman_prompt "${PROMPT_COMMAND:-:}")
fi
__cayman_accept() {
    if [[ $READLINE_LINE == @* ]]; then
        __cayman_emit request 0 "${READLINE_LINE:1}"
        READLINE_LINE=''
        READLINE_POINT=0
    else
        __cayman_emit start 0 "$READLINE_LINE"
    fi
}
__cayman_snapshot() { __cayman_emit input 0 "$READLINE_LINE"; }
__cayman_stage() {
    local expected_cwd expected candidate
    if [[ -f $__cayman_dir/stage ]]; then
        { IFS= read -r expected_cwd; IFS= read -r expected; IFS= read -r candidate; } < "$__cayman_dir/stage"
        if [[ $BASHPID == "$__cayman_pid" && $(builtin pwd -P) == "$expected_cwd" && $READLINE_LINE == "$expected" && -n $candidate ]]; then
            READLINE_LINE=$candidate
            READLINE_POINT=${#READLINE_LINE}
            __cayman_emit staged 0 "$READLINE_LINE"
        fi
        /bin/rm -f -- "$__cayman_dir/stage"
    fi
}
# A macro runs our widget first, then the standard accept-line operation. @ is
# removed before accept-line; normal commands retain normal Bash execution.
bind -x '"\C-x\C-a":__cayman_accept'
bind '"\C-x\C-b":accept-line'
bind '"\C-m":"\C-x\C-a\C-x\C-b"'
bind '"\C-j":"\C-x\C-a\C-x\C-b"'
bind '"\C-o":"\C-x\C-a\C-x\C-b"'
bind -x '"\C-x\C-g":__cayman_snapshot'
bind -x '"\C-xs":__cayman_stage'
