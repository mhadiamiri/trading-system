"""
Market Data Persistence

Append-only storage of raw market events to Parquet files.

Constitutional Principles:
- VIII. Total Observability & Provenance: Raw data append-only
"""

import os
from datetime import datetime, UTC
from decimal import Decimal
from typing import Optional
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

from trading.data.market_state import MarketState
from config.settings import Settings


class MarketDataPersistence:
    """
    Append-only storage for raw market events.

    Constitutional requirements:
    - Raw events are never mutated or rewritten
    - Data written to Parquet format
    - Append-only writes only
    """

    def __init__(self, data_dir: Optional[str] = None) -> None:
        """
        Initialize persistence layer.

        Args:
            data_dir: Directory for data files (default from settings)
        """
        self._data_dir = Path(data_dir or Settings.DATA_DIR)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # Current file handle
        self._writer: Optional[pq.ParquetWriter] = None
        self._current_file: Optional[Path] = None

        # Schema for market events (Sprint 2: quote-centric schema)
        self._schema = pa.schema([
            ("timestamp", pa.timestamp("ns")),
            ("symbol", pa.string()),
            ("best_bid", pa.string()),
            ("best_ask", pa.string()),
            ("best_bid_size", pa.string()),
            ("best_ask_size", pa.string()),
            ("mid_price", pa.string()),
            ("spread", pa.string()),
            ("trade_count", pa.int64()),
            ("total_volume", pa.string()),
            ("last_price", pa.string()),
        ])

        # Diagnostic counter
        self._rows_written = 0

    def _get_file_path(self) -> Path:
        """
        Get file path for current session.

        Returns:
            Path to Parquet file for current date/session
        """
        date_str = datetime.now(UTC).strftime("%Y%m%d")
        filename = f"market_events_{date_str}.parquet"
        return self._data_dir / filename

    def write_event(self, market_state: MarketState) -> None:
        """
        Write a market event to storage.

        Args:
            market_state: Market state to persist

        Constitutional requirements:
        - Append-only write (no mutation)
        """
        # Initialize writer if needed
        if self._writer is None or self._current_file != self._get_file_path():
            self._close_writer()
            self._current_file = self._get_file_path()

            # Create new writer (append mode if file exists)
            append_mode = self._current_file.exists()

            self._writer = pq.ParquetWriter(
                self._current_file,
                self._schema,
                compression="snappy",
                write_statistics=True,
            )

            if append_mode:
                # Verify file exists and is valid
                try:
                    existing = pq.read_table(self._current_file)
                    print(f"Appending to existing file: {self._current_file} "
                          f"({len(existing)} existing events)")
                except Exception as e:
                    print(f"Warning: Could not read existing file: {e}")
            else:
                print(f"Creating new data file: {self._current_file}")

        # Convert MarketState to Arrow record
        record = pa.record_batch([
            [market_state.timestamp],
            [market_state.symbol],
            [str(market_state.best_bid)],
            [str(market_state.best_ask)],
            [str(market_state.best_bid_size)],
            [str(market_state.best_ask_size)],
            [str(market_state.mid_price)],
            [str(market_state.spread)],
            [market_state.trade_count],
            [str(market_state.total_volume)],
            [str(market_state.last_price)] if market_state.last_price else [None],
        ], schema=self._schema)

        # Write to file
        self._writer.write_table(pa.Table.from_batches([record]))
        self._rows_written += 1

    def _close_writer(self) -> None:
        """Close current writer if open."""
        if self._writer is not None:
            self._writer.close()
            self._writer = None

    def close(self) -> None:
        """
        Close persistence layer and flush data.

        Call this when done writing events.
        """
        self._close_writer()
        if self._current_file and self._current_file.exists():
            print(f"Data file closed: {self._current_file}")

    def get_file_info(self) -> dict:
        """
        Get information about current data file.

        Returns:
            Dict with file info (path, exists, size, event_count, rows_written)
        """
        file_path = self._get_file_path()
        info = {
            "path": str(file_path),
            "exists": file_path.exists(),
            "size_bytes": 0,
            "event_count": 0,
            "rows_written": self._rows_written,
        }

        if file_path.exists():
            info["size_bytes"] = file_path.stat().st_size
            try:
                table = pq.read_table(file_path)
                info["event_count"] = len(table)
            except Exception as e:
                print(f"Warning: Could not read data file: {e}")

        return info

    def get_rows_written(self) -> int:
        """
        Get the number of rows written in this session.

        Returns:
            Number of rows written
        """
        return self._rows_written

    def reset_counter(self) -> None:
        """Reset the rows written counter."""
        self._rows_written = 0

    def __del__(self):
        """Cleanup on deletion."""
        self._close_writer()
