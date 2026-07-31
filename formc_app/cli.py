from __future__ import annotations

import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Yeratta Form C application")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    os.environ["FORMC_DATA_DIR"] = args.data_dir
    uvicorn.run("formc_app.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
