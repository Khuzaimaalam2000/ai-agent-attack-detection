import json
from pathlib import Path


def convert_trial(trace_path):
    messages = []
    pending_tool_ids = []

    with open(trace_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            kind = rec.get("kind")

            if kind == "decide":
                text_parts = []
                content = rec.get("content", [])
                if isinstance(content, str):
                    text_parts.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            text_parts.append(block)

                tool_calls_out = []
                for tc in rec.get("tool_calls", []):
                    tool_calls_out.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc.get("args", {})),
                        },
                    })
                    pending_tool_ids.append(tc["id"])

                msg = {"role": "assistant", "content": "\n".join(text_parts) if text_parts else None}
                if tool_calls_out:
                    msg["tool_calls"] = tool_calls_out
                messages.append(msg)

            elif kind == "act":
                tool_call_id = pending_tool_ids.pop(0) if pending_tool_ids else None
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": str(rec.get("tool_output", "")),
                })

    return {"messages": messages}


def main():
    runs_dir = Path("runs")
    out_dir = Path("quarry_input")
    out_dir.mkdir(exist_ok=True)

    count = 0
    failed = []
    for trial_dir in sorted(runs_dir.iterdir()):
        trace_path = trial_dir / "agent_trace.jsonl"
        if not trace_path.exists():
            continue
        try:
            converted = convert_trial(trace_path)
        except Exception as e:
            failed.append((trial_dir.name, str(e)))
            continue
        out_path = out_dir / f"{trial_dir.name}.json"
        with open(out_path, "w") as f:
            json.dump(converted, f, indent=2)
        count += 1

    print(f"Converted {count} trials to {out_dir}/")
    if failed:
        print(f"Failed ({len(failed)}):")
        for name, err in failed:
            print(f"  {name}: {err}")


if __name__ == "__main__":
    main()