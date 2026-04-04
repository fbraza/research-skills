# whimsical

## Summary

`whimsical` replaces the default working message with random playful status text while Pi is processing a turn.

## What it adds

- No commands or tools
- Turn lifecycle hooks on `turn_start` and `turn_end`

## How it works

- Chooses a random message from a long built-in list
- Sets that message as the working message at turn start
- Clears the working message at turn end

## Usage

Use this when you want lighter, more playful UI feedback during processing.

## Examples

- Start any agent turn and watch the working message change to a random phrase such as “Percolating...” or “Baking at 350 kilobytes...”

## Files and state

- No project files
- No persistent state

## Notes / caveats

- Purely cosmetic
- The working message changes randomly on each turn
