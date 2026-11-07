# Turns pyright's JSON output (pyright --outputjson) into GitHub workflow commands: one annotation
# per finding, then a line with the counts. $root is the repository's path with a trailing slash,
# cut from the file names.
def escape: gsub("%"; "%25") | gsub("\r"; "%0D") | gsub("\n"; "%0A");

(.generalDiagnostics[]
 | "::\(if .severity == "information" then "notice" else .severity end)"
   + " file=\(.file // "" | ltrimstr($root)),line=\((.range.start.line // 0) + 1)"
   + ",col=\((.range.start.character // 0) + 1)"
   + "::\(.message + (if .rule then " (\(.rule))" else "" end) | escape)"),
(.summary | "pyright: \(.errorCount) errors, \(.warningCount) warnings, \(.informationCount) notes")
