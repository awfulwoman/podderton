import subscribe
import publish
import server

def main(args):
    print("WARNING: Running in single-process mode. Use run_subscriber.py and run_generator.py for production.")
    print("Welcome to Podderton!")
    print("Using configuration from:", args[0])

    subscribe.main(args[0])
    publish.main(args[0])
    server.main(args[0])

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])