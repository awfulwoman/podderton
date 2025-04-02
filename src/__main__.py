import subscribe

def main(args):
    print("Welcome to Podderton!")
    print("Config file: ", args[0])

    subscribe.main(args[0])
    # generate.main(args[0])
  
if __name__ == "__main__":
    import sys
    main(sys.argv[1:])