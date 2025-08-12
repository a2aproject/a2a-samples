import os
import sys


class ConsoleReader:

    def __iter__(self) -> "ConsoleReader":
        print("Interactive session has started. To escape, input 'q' and submit.")
        return self

    def __next__(self) -> str:
        try:
            while True:
                prompt = input("User 👤 : ").strip()
                if not sys.stdin.isatty() and "PYCHARM_HOSTED" not in os.environ:
                    print(prompt)

                if prompt == "q":
                    raise StopIteration

                if not prompt:
                    print("Error: Empty prompt is not allowed. Please try again.")
                    continue

                return prompt
        except (EOFError, KeyboardInterrupt):
            print()
            exit()

    def write(self, role: str, data: str) -> None:
        print(role, data)
        
