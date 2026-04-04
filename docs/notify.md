# notify

## Summary

`notify` sends a native desktop notification when the agent finishes responding and is waiting for input.

## What it adds

- No commands or tools
- Agent lifecycle hook on `agent_end`

## How it works

- Extracts the last assistant text from the completed turn
- Converts markdown to simplified plain text
- Sends a native notification using OSC 777 escape sequences

## Usage

Use this when you want background notification support while Pi is running in a compatible terminal.

## Examples

- Let Pi work in another terminal tab and wait for a desktop notification when it finishes

## Files and state

- No project files
- No persistent state

## Notes / caveats

- Terminal support is limited to terminals that understand OSC 777 notifications
- Not all terminals support this escape sequence
- Notifications are best-effort and depend on the terminal environment
