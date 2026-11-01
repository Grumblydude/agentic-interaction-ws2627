"""Entry point: python -m agent "<task>"."""
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python -m agent "<task>"', file=sys.stderr)
        return 2
    task = sys.argv[1]
    # TODO (Exercise 1): call the model with the calendar tool and print its answer.
    print(f"Agent not implemented yet. Task: {task}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
