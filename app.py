"""Web chat (Gradio). This is the entry point on Hugging Face Spaces; run locally with `python app.py`."""
import gradio as gr

from agent.agent import answer

EXAMPLES = [
    "Which vendors chase us for payment, and how far did each go?",
    "Which chased invoices are not in the inbox?",
    "How many invoices did we receive, and what is their total?",
    "Which files could not be read?",
    "How accurate are you?",
]


def respond(message, history):
    text, trace = answer(message, [{"role": h["role"], "content": h["content"]} for h in history
                                   if isinstance(h.get("content"), str)])
    if trace:
        text += "\n\n<details><summary>How I got this</summary>\n\n" + \
                "\n".join(f"- `{t[:300]}`" for t in trace) + "\n</details>"
    return text


demo = gr.ChatInterface(
    respond, title="AP Inbox Agent",
    description="Ask about one month of an accounts-payable inbox (5,705 emails, 8,554 attachments). "
                "Answers cite email/file IDs and flag anything unreadable, missing or uncertain.",
    examples=EXAMPLES)

if __name__ == "__main__":
    demo.launch()
