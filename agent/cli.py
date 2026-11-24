"""Command-line chat: python -m agent.cli"""
from agent.agent import answer


def main():
    history = []
    print("AP Inbox Agent - ask a question (Ctrl-D to quit)")
    while True:
        try:
            q = input("\n> ").strip()
        except EOFError:
            break
        if not q:
            continue
        text, trace = answer(q, history)
        for t in trace:
            print(f"  · {t[:200]}")
        print(text)
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": text}]


if __name__ == "__main__":
    main()
