"""Agent command handler."""
import getpass
import os
import sys
import warnings


def agent_command(args):
    """Route agent commands."""
    from avcpm_agent import create_agent, list_agents, get_agent

    base_dir = _get_base_dir(args)

    if args.subcommand == "create":
        if not args.name or not args.email:
            print("Error: agent create requires name and email")
            sys.exit(1)

        encrypt = not getattr(args, 'no_encrypt', False)
        passphrase = None

        if encrypt:
            # Check --passphrase arg, then env var, then prompt
            passphrase = getattr(args, 'passphrase', None)
            if not passphrase:
                passphrase = os.environ.get("AVCPM_KEY_PASSPHRASE")
            if not passphrase:
                passphrase = getpass.getpass("Enter passphrase for private key encryption: ")
                confirm = getpass.getpass("Confirm passphrase: ")
                if passphrase != confirm:
                    print("Error: Passphrases do not match")
                    sys.exit(1)
            if len(passphrase) < 8:
                print("Error: Passphrase must be at least 8 characters")
                sys.exit(1)
        else:
            warnings.warn(
                "Private key will be stored unencrypted. This is NOT recommended "
                "for production use. Anyone with filesystem access can read the key.",
                UserWarning,
                stacklevel=2,
            )

        try:
            agent = create_agent(args.name, args.email, base_dir, passphrase=passphrase, encrypt=encrypt)
            print(f"Agent created successfully!")
            print(f"  ID: {agent['agent_id']}")
            print(f"  Name: {agent['name']}")
            print(f"  Email: {agent['email']}")
            if encrypt:
                print(f"  Encryption: Enabled (AES-256-GCM)")
            else:
                print(f"  Encryption: DISABLED (private key stored unencrypted)")
        except Exception as e:
            print(f"Error creating agent: {e}")
            sys.exit(1)

    elif args.subcommand == "list":
        agents = list_agents(base_dir)
        if not agents:
            print("No agents registered.")
        else:
            print("Registered Agents:")
            print("-" * 60)
            for agent_id, info in agents.items():
                print(f"  ID: {agent_id}")
                print(f"  Name: {info.get('name', 'N/A')}")
                print(f"  Email: {info.get('email', 'N/A')}")
                print("-" * 60)

    elif args.subcommand == "show":
        if not args.agent_id:
            print("Error: agent show requires agent_id")
            sys.exit(1)
        agent = get_agent(args.agent_id, base_dir)
        if agent:
            print(f"Agent: {agent['name']}")
            print(f"  ID: {agent['agent_id']}")
            print(f"  Email: {agent['email']}")
            print(f"  Created: {agent['created_at']}")
        else:
            print(f"Agent {args.agent_id} not found.")
            sys.exit(1)

    else:
        print(f"Unknown agent subcommand: {args.subcommand}")
        sys.exit(1)


def _get_base_dir(args):
    """Get base directory from args."""
    if hasattr(args, 'base_dir') and args.base_dir:
        return args.base_dir
    return ".avcpm"