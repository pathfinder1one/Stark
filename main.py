"""
STARK — Main Entry Point

Usage:
    python main.py                      # interactive chat
    python main.py --mode fast          # force fast mode
    python main.py --query "Your query" # single shot
    python main.py --serve              # start API server (Phase 6)
"""
from __future__ import annotations

import asyncio
import argparse
import sys

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from stark import STARKEngine, __version__


async def interactive_chat(engine: STARKEngine, default_mode: str = "auto") -> None:
    """Run an interactive terminal chat with STARK."""
    print(f"\n{'='*60}")
    print(f"  ⚡ STARK v{__version__} — Local Cognitive AI")
    print(f"  Model: qwen3.5:4b | Mode: {default_mode}")
    print(f"  Type 'quit' or 'exit' to stop")
    print(f"  Prefix with @fast / @reasoning / @deep / @auto to override mode")
    print(f"{'='*60}\n")

    session_id = None  # Will be set on first response

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue

        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye! 👋")
            break

        # Check for mode override prefix
        mode = default_mode
        if user_input.startswith("@"):
            parts = user_input.split(" ", 1)
            mode_tag = parts[0][1:].lower()  # e.g. "fast"
            if mode_tag in {"fast", "reasoning", "deep", "auto", "autonomous"}:
                mode = mode_tag
                user_input = parts[1] if len(parts) > 1 else ""
                if not user_input:
                    print("Please provide a message after the mode tag.\n")
                    continue

        print(f"\nSTARK [{mode}]: ", end="", flush=True)

        try:
            response = await engine.run(
                message=user_input,
                mode=mode,
                session_id=session_id,
            )
            session_id = response.session_id  # Persist session

            print(response.answer)
            print(
                f"\n  ─── [{response.mode_used} | "
                f"{response.total_latency_ms:.0f}ms | "
                f"agents: {', '.join(response.agents_used) or 'none'}"
                + (f" | score: {response.judge_score:.0f}" if response.judge_score else "")
                + "] ───\n"
            )

        except Exception as e:
            print(f"\n[ERROR] {e}\n")


async def single_query(engine: STARKEngine, query: str, mode: str) -> None:
    """Run a single query and print the result."""
    print(f"\nQuery: {query}")
    print(f"Mode:  {mode}\n")

    response = await engine.run(message=query, mode=mode)

    print("=" * 60)
    print(response.answer)
    print("=" * 60)
    print(f"Mode:     {response.mode_used}")
    print(f"Agents:   {', '.join(response.agents_used) or 'none'}")
    print(f"Score:    {f'{response.judge_score:.1f}/100' if response.judge_score else 'N/A'}")
    print(f"Latency:  {response.total_latency_ms:.0f}ms")
    print(f"Tokens:   {response.total_tokens}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="STARK — Local Cognitive AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode", "-m",
        default="auto",
        choices=["auto", "fast", "reasoning", "deep", "autonomous"],
        help="Execution mode (default: auto)",
    )
    parser.add_argument(
        "--query", "-q",
        default=None,
        help="Single query (non-interactive mode)",
    )
    parser.add_argument(
        "--model",
        default="qwen3.5:4b",
        help="Ollama model to use (default: qwen3.5:4b)",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama server URL",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the STARK FastAPI server",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind server to (default: 8000)",
    )
    args = parser.parse_args()

    if args.serve:
        import uvicorn
        print(f"\n⚡ Starting STARK API server on http://{args.host}:{args.port} ...")
        config = uvicorn.Config("stark.api.server:app", host=args.host, port=args.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
        return

    # Boot the engine
    engine = STARKEngine(model=args.model, ollama_url=args.ollama_url)

    print("Starting STARK...")
    try:
        await engine.startup()
    except RuntimeError as e:
        print(f"\n[STARTUP ERROR] {e}")
        sys.exit(1)

    # Run
    if args.query:
        await single_query(engine, args.query, args.mode)
    else:
        await interactive_chat(engine, default_mode=args.mode)


if __name__ == "__main__":
    asyncio.run(main())
