# Agent policy (blast-radius decisions)

- Bash(rm *): the reviewer reads and comments; deleting files is the author's decision, never the reviewer's.
- Bash(git push *): pushing publishes the submission tag, so only the author pushes after a green verify run.
- Bash(docker *): containers belong to the checker run; the reviewer must never restart, stop or remove them.
- WebFetch: the contract lives in the repository docs, so the reviewer works offline and never fetches the network.
