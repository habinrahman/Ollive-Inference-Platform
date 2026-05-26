from __future__ import annotations

import argparse
import json
import time

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Exercise chat, ingestion, Supabase persistence, and analytics.")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--require-success", action="store_true")
    args = parser.parse_args()

    payload = {
        "message": "E2E smoke test for Ollive inference telemetry.",
        "session_id": "e2e-smoke",
        "provider": args.provider,
    }

    with httpx.Client(timeout=60) as client:
        health = client.get(f"{args.api_base_url}/health")
        health.raise_for_status()

        if args.stream:
            chunks = []
            current_event = None
            saw_error = False
            saw_done = False
            with client.stream("POST", f"{args.api_base_url}/v1/chat/stream", json=payload) as response:
                print(f"stream_status={response.status_code}")
                if args.require_success:
                    response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("event: "):
                        current_event = line.removeprefix("event: ")
                        saw_error = saw_error or current_event == "error"
                        saw_done = saw_done or current_event == "done"
                        print(line)
                    if line.startswith("data: ") and current_event == "token":
                        chunks.append(line)
            if args.require_success and saw_error:
                raise SystemExit("Streaming response emitted an error event.")
            if args.require_success and (not saw_done or not chunks):
                raise SystemExit("Streaming response did not complete successfully.")
            print(f"stream_token_events={len(chunks)}")
        else:
            response = client.post(f"{args.api_base_url}/v1/chat", json=payload)
            print(f"chat_status={response.status_code}")
            print(response.text[:500])
            if args.require_success:
                response.raise_for_status()

        time.sleep(3)
        analytics = client.get(f"{args.api_base_url}/v1/analytics/summary?hours=24")
        analytics.raise_for_status()
        summary = analytics.json()

    recent = summary.get("recent_inferences", [])[:3]
    print(
        json.dumps(
            {
                "total_requests": summary.get("total_requests"),
                "error_rate": summary.get("error_rate"),
                "ingestion_states": summary.get("ingestion_states"),
                "recent_inferences": recent,
            },
            indent=2,
        )
    )

    if not recent:
        raise SystemExit("No recent inference events found in analytics output.")


if __name__ == "__main__":
    main()
