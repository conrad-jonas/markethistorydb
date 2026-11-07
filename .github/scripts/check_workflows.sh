#!/usr/bin/env bash
# Checks the workflows in .github/workflows, or in the directory given as the first argument:
# - every action is referenced by a full 40-character commit SHA, never by a tag or a branch;
# - no workflow is triggered by pull_request_target;
# - no workflow triggered by pull_request names the environment nightly or the eodhd.com token.
# Prints each finding as a GitHub annotation and exits with 1 if there is any.
set -u

directory=${1:-.github/workflows}
status=0

report() {
    echo "::error file=$1,line=$2::$3"
    status=1
}

for workflow in "$directory"/*.yml "$directory"/*.yaml; do
    [ -e "$workflow" ] || continue

    while IFS=: read -r line text; do
        if ! grep -qE 'uses:[[:space:]]+[^@[:space:]]+@[0-9a-f]{40}([[:space:]]|$)' <<< "$text"; then
            report "$workflow" "$line" "Action not pinned to a full commit SHA"
        fi
    done < <(grep -nE '^[[:space:]]*(-[[:space:]]+)?uses:' "$workflow")

    while IFS=: read -r line _; do
        report "$workflow" "$line" "pull_request_target runs with the repository's secrets"
    done < <(grep -n 'pull_request_target' "$workflow")

    # -w leaves out pull_request_target; a mere mention of pull_request counts, to be safe
    if grep -qw 'pull_request' "$workflow"; then
        while IFS=: read -r line _; do
            report "$workflow" "$line" "A workflow triggered by pull_request names the eodhd.com token"
        done < <(grep -n 'EODHD_API_TOKEN' "$workflow")
        # "environment: nightly", or "name: nightly" within the two lines after "environment:"
        while read -r line; do
            report "$workflow" "$line" "A workflow triggered by pull_request names the environment nightly"
        done < <(awk '/^[[:space:]]*environment:/ { opened = NR }
                      /nightly/ && opened && NR - opened <= 2 { print NR }' "$workflow")
    fi
done

exit $status
