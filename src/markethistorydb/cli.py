"""Command line interface: `markethistorydb fetch|setup`"""

import argparse

from markethistorydb.utils.categories import SymbolStatus, TimeFrame


def _enum_arg(enum_cls):
    def parse(value: str):
        try:
            return enum_cls[value.upper()]
        except KeyError:
            names = ", ".join(member.name.lower() for member in enum_cls)
            raise argparse.ArgumentTypeError("invalid choice '{0}' (choose from {1})".format(value, names))
    return parse

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="markethistorydb", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="fetch data from eodhd.com and insert it into the DB")
    fetch_parser.add_argument("--time-frame", type=_enum_arg(TimeFrame), default=None)
    fetch_parser.add_argument("--symbol-status", type=_enum_arg(SymbolStatus), default=None)
    fetch_parser.add_argument("--exchange", default=None, help="restrict fetching to one exchange name")

    subparsers.add_parser("setup", help="set up the QuestDB tables (asks for confirmation)")
    return parser

def main(argv: list[str] | None = None):
    args = _build_parser().parse_args(argv)
    # Imported lazily so that `--help` works without DB/API configuration
    if args.command == "fetch":
        from markethistorydb.fetch.main import main as fetch_main
        fetch_main(args.time_frame, args.symbol_status, args.exchange)
    elif args.command == "setup":
        from markethistorydb.setup.main import main as setup_main
        setup_main()

if __name__ == "__main__":
    main()
