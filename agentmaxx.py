#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from providers import PROVIDERS


ROOT = Path(__file__).resolve().parent


def detect_providers():
    return [
        provider
        for provider in PROVIDERS.values()
        if provider.is_installed()
    ]


def _resolve_providers(provider_name: str | None) -> list:
    if provider_name:
        return [PROVIDERS[provider_name]]
    return detect_providers()


def install_global(provider_name: str | None) -> None:
    """Install skills and tools into every detected provider's global config."""
    providers = _resolve_providers(provider_name)

    if not providers:
        print("No supported agent providers detected.")
        return

    for provider_type in providers:
        print(f"Installing agent maxx globally for {provider_type.name}")

        provider_type(source_root=ROOT).install_global()

    print("agent maxx global installation complete.")


def init(provider_name: str | None) -> None:
    """Inject the output-contract template into the current repo's rules file."""
    providers = _resolve_providers(provider_name)

    if not providers:
        print("No supported agent providers detected.")
        return

    repo_root = Path.cwd()

    for provider_type in providers:
        if not provider_type.supports_local_rules:
            print(
                f"skip  {provider_type.name}: no per-repo personal rules file; "
                "global install covers every repo"
            )
            continue

        print(f"Initializing agent maxx for {provider_type.name} in {repo_root}")

        provider_type(source_root=ROOT).install_repo(repo_root)

    print("agent maxx repo initialization complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agentmaxx",
        description="Agent productivity tools and workflows.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    install_parser = subparsers.add_parser(
        "install",
        help="Install agent maxx skills/tools into detected providers' global config.",
    )

    install_parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        help="Install for a specific provider.",
    )

    init_parser = subparsers.add_parser(
        "init",
        help="Add the agent maxx output contract to the current repo.",
    )

    init_parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        help="Initialize a specific provider.",
    )

    args = parser.parse_args()

    if args.command == "install":
        install_global(args.provider)
    elif args.command == "init":
        init(args.provider)


if __name__ == "__main__":
    main()