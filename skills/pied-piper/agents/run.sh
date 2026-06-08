#!/usr/bin/env zsh
# pi-agent dispatcher — run any pi agent by name
# Usage: run.sh <agent> <task>
# Agents: explore | debug | trace | exec | review | security | qa | playwright
#
# Examples:
#   run.sh explore "find all uses of get_current_site in /path/to/repo"
#   run.sh debug "AttributeError: NoneType at lms/views.py:142 after login"
#   run.sh playwright "navigate to https://example.com and verify the title"

AGENT="${1:-}"
shift
TASK="${*:-}"

AGENTS_DIR="${0:A:h}"

case "$AGENT" in
  explore|ex)       exec "$AGENTS_DIR/explore.sh" "$TASK" ;;
  debug|debugger)   exec "$AGENTS_DIR/debugger.sh" "$TASK" ;;
  trace|tracer)     exec "$AGENTS_DIR/tracer.sh" "$TASK" ;;
  exec|executor)    exec "$AGENTS_DIR/executor.sh" "$TASK" ;;
  review|reviewer)  exec "$AGENTS_DIR/reviewer.sh" "$TASK" ;;
  security|sec)     exec "$AGENTS_DIR/security.sh" "$TASK" ;;
  qa|tmux)          exec "$AGENTS_DIR/qa-tmux.sh" "$TASK" ;;
  playwright|pw)    exec "$AGENTS_DIR/playwright.sh" "$TASK" ;;
  *)
    print "Usage: run.sh <agent> <task>"
    print ""
    print "Agents:"
    print "  explore   (ex)      — codebase search, find files/patterns [fast model]"
    print "  debug     (debugger) — root-cause analysis [reason model]"
    print "  trace     (tracer)  — causal tracing with competing hypotheses [reason model]"
    print "  exec      (executor) — minimal implementation [reason model, can write]"
    print "  review    (reviewer) — severity-rated code review [fast model]"
    print "  security  (sec)     — OWASP audit + secrets scan [reason model]"
    print "  qa        (tmux)    — interactive CLI testing via tmux [reason model]"
    print "  playwright (pw)     — browser automation via Playwright MCP [reason model]"
    exit 1
    ;;
esac
