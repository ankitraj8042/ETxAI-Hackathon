"""
DCBrain Agent Cascade Bus
Handles event routing between specialized agents and broadcasts events
to the frontend client in real-time.
"""

import json
import asyncio
from typing import Dict, List, Callable, Any, Awaitable
from uuid import uuid4
from datetime import datetime

from app.core.dependencies import get_redis


class CascadeEventPayload:
    """Structured payload for events running through the cascade bus."""

    def __init__(
        self,
        source_agent: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        summary: str,
        details: Dict[str, Any] = None,
        explainability: Dict[str, Any] = None,
        trace_id: str = None,
        severity: str = "info"
    ):
        self.id = str(uuid4())
        self.trace_id = trace_id or f"trace-{int(datetime.utcnow().timestamp())}"
        self.source_agent = source_agent
        self.event_type = event_type
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.summary = summary
        self.details = details or {}
        self.explainability = explainability or {}
        self.severity = severity
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert payload to serializeable dict."""
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "source_agent": self.source_agent,
            "event_type": self.event_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "summary": self.summary,
            "details": self.details,
            "explainability": self.explainability,
            "severity": self.severity,
            "created_at": self.created_at
        }


# Type signature for asynchronous event handlers
EventHandler = Callable[[CascadeEventPayload], Awaitable[None]]


class CascadeBus:
    """Event bus that manages event subscriptions and handles event propagation."""

    def __init__(self):
        self._listeners: Dict[str, List[EventHandler]] = {}
        self._active_connections: List[Any] = []

    def subscribe(self, event_type: str, handler: EventHandler):
        """Register an agent handler to listen for a specific event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(handler)
        print(f"⚡ CascadeBus: Subscribed handler to event '{event_type}'")

    async def publish(self, event: CascadeEventPayload):
        """Publish an event to the bus, trigger handlers, and broadcast to frontend."""
        event_dict = event.to_dict()
        print(f"📣 CascadeBus Event: [{event.source_agent.upper()}] {event.summary} (Trace: {event.trace_id})")

        # 1. Save event to relational database for audit log
        try:
            # Import database locally to avoid circular dependencies
            from app.core.database import async_session_factory
            from app.models.knowledge import CascadeEvent
            from uuid import UUID as parse_uuid
            
            async with async_session_factory() as session:
                db_event = CascadeEvent(
                    id=parse_uuid(event.id),
                    trace_id=event.trace_id,
                    source_agent=event.source_agent,
                    event_type=event.event_type,
                    severity=event.severity,
                    entity_type=event.entity_type,
                    entity_id=event.entity_id,
                    summary=event.summary,
                    details=event.details,
                    explainability=event.explainability
                )
                session.add(db_event)
                await session.commit()
        except Exception as e:
            print(f"⚠️ CascadeBus: Failed to log event to database: {e}")

        # 2. Broadcast event to active WebSockets (Frontend)
        await self.broadcast_to_frontend(event_dict)

        # 3. Publish to Redis channel (if Redis is running)
        try:
            redis_client = await get_redis()
            await redis_client.publish("cascade", json.dumps(event_dict))
        except Exception:
            pass

        # 4. Trigger registered local async handlers
        handlers = self._listeners.get(event.event_type, [])
        for handler in handlers:
            # Run handler in background task to avoid blocking the bus
            asyncio.create_task(self._safe_execute(handler, event))

    async def _safe_execute(self, handler: EventHandler, event: CascadeEventPayload):
        """Execute a handler safely, catching exceptions."""
        try:
            await handler(event)
        except Exception as e:
            print(f"❌ CascadeBus: Error executing handler for {event.event_type}: {e}")

    # ── WebSocket Broadcast Support ─────────────────────────────────────

    def register_websocket(self, websocket: Any):
        """Register a frontend WebSocket connection."""
        self._active_connections.append(websocket)
        print(f"🔌 CascadeBus: WebSocket connection registered. Active: {len(self._active_connections)}")

    def unregister_websocket(self, websocket: Any):
        """Unregister a frontend WebSocket connection."""
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)
            print(f"🔌 CascadeBus: WebSocket connection removed. Active: {len(self._active_connections)}")

    async def broadcast_to_frontend(self, message: Dict[str, Any]):
        """Send message to all registered active WebSocket clients."""
        if not self._active_connections:
            return

        payload_str = json.dumps(message)
        # Snapshot connections to avoid mutation during iteration
        connections = list(self._active_connections)

        async def _safe_send(conn):
            try:
                await conn.send_text(payload_str)
                return None
            except Exception:
                return conn

        results = await asyncio.gather(*[_safe_send(c) for c in connections])
        # Clean up dead connections
        for conn in results:
            if conn is not None:
                self.unregister_websocket(conn)


# Global bus instance
cascade_bus = CascadeBus()
