# answer

## Summary

`answer` extracts follow-up questions from the last assistant message, presents them in an interactive TUI, and sends the collected answers back into the conversation.

## What it adds

- Command: `/answer`
- Shortcut: `Ctrl+.`

## How it works

- Reads the last assistant message in the session
- Uses an LLM with a structured JSON prompt to extract questions
- Opens a custom Q&A interface so the user can answer each question
- Sends the compiled answers back as a new message and triggers another turn
- Prefers `gpt-5.1-codex-mini` when available, otherwise falls back to Haiku or the current model

## Usage

Use this when the assistant asked multiple questions in one response and you want a structured way to answer them all at once.

## Examples

- `/answer`
- Press `Ctrl+.` after the assistant asks for several configuration choices

## Files and state

- No project files are written directly by the extension
- Uses session messages only

## Notes / caveats

- Works best when the last assistant message actually contains explicit questions
- If no questions are extracted, the command does nothing useful
- This extension is a prompt-generation helper, not a persistent form system
