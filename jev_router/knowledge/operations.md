# Operations, privacy, and limits

Live requests send the question and up to three bundled documentation passages to
TypeSafe. Questions sent to Qwen travel to the configured local gateway. Use synthetic
or public data for this portfolio project. No chat history is stored server-side.
Application metrics contain only bounded route, mode, and outcome labels, never
questions, answers, keys, or user identities. The SDK's debug body logging is disabled.

The router allows four active requests and thirty requests per minute per process.
Requests have a 45-second total deadline and an 8-second Jev decision deadline.
Question length is limited to 4000 characters, body size to 16 KiB, and output to
512 tokens. Limits are local to one worker; run one worker. Auth is required in live
mode. Bind to localhost by default. Hosted deployments need TLS and managed secrets.
The .env file is excluded from Git and Docker builds. Only .env.example is published.
