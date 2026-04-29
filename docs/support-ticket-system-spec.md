# Support Ticket System - Technical Specification

## Overview

This document outlines the design and implementation plan for an integrated support ticket system within the AI-Identity platform. The system will allow customers to create support tickets directly from the dashboard, with full context awareness of their organization, agents, and audit logs.

## Architecture

### Database Schema

#### `support_tickets` Table

```sql
CREATE TABLE support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_number VARCHAR(20) UNIQUE NOT NULL,  -- e.g., "TKT-2024-0001"
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,

    -- Ticket content
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(20) NOT NULL,  -- 'low', 'medium', 'high', 'urgent'
    status VARCHAR(20) NOT NULL,    -- 'open', 'in_progress', 'waiting_customer', 'resolved', 'closed'
    category VARCHAR(50),           -- 'technical', 'billing', 'feature_request', 'bug', 'other'

    -- Context linking
    related_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    related_audit_log_ids JSONB,   -- Array of audit log IDs for context

    -- Assignment
    assigned_to_user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,

    -- Indexes
    INDEX idx_tickets_user_id (user_id),
    INDEX idx_tickets_org_id (org_id),
    INDEX idx_tickets_status (status),
    INDEX idx_tickets_priority (priority),
    INDEX idx_tickets_assigned_to (assigned_to_user_id),
    INDEX idx_tickets_created_at (created_at DESC)
);
```

#### `ticket_comments` Table

```sql
CREATE TABLE ticket_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Comment content
    content TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT FALSE,  -- Internal notes vs customer-visible

    -- Attachments (future enhancement)
    attachments JSONB DEFAULT '[]',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes
    INDEX idx_comments_ticket_id (ticket_id, created_at),
    INDEX idx_comments_user_id (user_id)
);
```

### Data Models

#### SQLAlchemy Models

**Location:** `common/models/support_ticket.py`

```python
from enum import Enum
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from common.models.base import Base
import uuid
from datetime import datetime, UTC

class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketCategory(str, Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    FEATURE_REQUEST = "feature_request"
    BUG = "bug"
    OTHER = "other"

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_number = Column(String(20), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"))

    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default=TicketPriority.MEDIUM)
    status = Column(String(20), nullable=False, default=TicketStatus.OPEN)
    category = Column(String(50))

    related_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))
    related_audit_log_ids = Column(JSONB, default=[])

    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    metadata = Column(JSONB, default={})

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    resolved_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="tickets")
    organization = relationship("Organization", back_populates="tickets")
    related_agent = relationship("Agent")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tickets_user_id", "user_id"),
        Index("idx_tickets_org_id", "org_id"),
        Index("idx_tickets_status", "status"),
        Index("idx_tickets_priority", "priority"),
        Index("idx_tickets_assigned_to", "assigned_to_user_id"),
        Index("idx_tickets_created_at", "created_at"),
    )

class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    attachments = Column(JSONB, default=[])

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    ticket = relationship("SupportTicket", back_populates="comments")
    user = relationship("User")

    __table_args__ = (
        Index("idx_comments_ticket_id", "ticket_id", "created_at"),
        Index("idx_comments_user_id", "user_id"),
    )
```

#### Pydantic Schemas

**Location:** `common/schemas/support_ticket.py`

```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, UUID4
from common.models.support_ticket import TicketPriority, TicketStatus, TicketCategory

# Request schemas
class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)
    priority: TicketPriority = TicketPriority.MEDIUM
    category: Optional[TicketCategory] = None
    related_agent_id: Optional[UUID4] = None
    related_audit_log_ids: Optional[List[str]] = None

class TicketUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    priority: Optional[TicketPriority] = None
    status: Optional[TicketStatus] = None
    category: Optional[TicketCategory] = None
    assigned_to_user_id: Optional[UUID4] = None

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    is_internal: bool = False

# Response schemas
class CommentResponse(BaseModel):
    id: UUID4
    ticket_id: UUID4
    user_id: UUID4
    user_email: str
    content: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime

class TicketResponse(BaseModel):
    id: UUID4
    ticket_number: str
    user_id: UUID4
    org_id: Optional[UUID4]
    subject: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    category: Optional[TicketCategory]
    related_agent_id: Optional[UUID4]
    related_agent_name: Optional[str]
    related_audit_log_ids: Optional[List[str]]
    assigned_to_user_id: Optional[UUID4]
    assigned_to_email: Optional[str]
    comment_count: int
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]

class TicketDetailResponse(TicketResponse):
    comments: List[CommentResponse]
    user_email: str
    org_name: Optional[str]

class TicketListResponse(BaseModel):
    items: List[TicketResponse]
    total: int
    limit: int
    offset: int
```

### API Endpoints

**Location:** `api/app/routers/support_tickets.py`

#### Endpoints

1. **POST /api/v1/tickets** - Create a new ticket
   - Auth: Requires authenticated user
   - Body: `TicketCreate`
   - Returns: `TicketDetailResponse`

2. **GET /api/v1/tickets** - List tickets
   - Auth: Requires authenticated user
   - Query params: `status`, `priority`, `category`, `limit`, `offset`
   - Returns: `TicketListResponse`
   - Users see their own tickets; admins see all

3. **GET /api/v1/tickets/{ticket_id}** - Get ticket details
   - Auth: Requires authenticated user (owner or admin)
   - Returns: `TicketDetailResponse`

4. **PATCH /api/v1/tickets/{ticket_id}** - Update ticket
   - Auth: Requires authenticated user (owner or admin)
   - Body: `TicketUpdate`
   - Returns: `TicketDetailResponse`

5. **POST /api/v1/tickets/{ticket_id}/comments** - Add comment
   - Auth: Requires authenticated user (owner or admin)
   - Body: `CommentCreate`
   - Returns: `CommentResponse`

6. **GET /api/v1/tickets/{ticket_id}/context** - Get related context
   - Auth: Requires authenticated user (owner or admin)
   - Returns: Related agent details, recent audit logs, etc.

### Frontend Components

#### Pages

1. **SupportTicketsPage** (`dashboard/src/pages/SupportTicketsPage.tsx`)
   - List view with filters (status, priority, category)
   - Search by ticket number or subject
   - Create new ticket button
   - Ticket cards showing key info
   - Click to view details

2. **TicketDetailPage** (`dashboard/src/pages/TicketDetailPage.tsx`)
   - Full ticket details
   - Comment thread
   - Related context (agent, audit logs)
   - Status update controls
   - Add comment form

#### Components

1. **CreateTicketModal** (`dashboard/src/components/modals/CreateTicketModal.tsx`)
   - Form with subject, description, priority, category
   - Optional agent selection dropdown
   - Form validation
   - Success/error handling

2. **TicketCard** (`dashboard/src/components/support/TicketCard.tsx`)
   - Compact ticket display for list view
   - Status badge, priority indicator
   - Timestamp, comment count

3. **TicketFilters** (`dashboard/src/components/support/TicketFilters.tsx`)
   - Filter by status, priority, category
   - Search input
   - Clear filters button

4. **CommentThread** (`dashboard/src/components/support/CommentThread.tsx`)
   - Display all comments
   - User avatars, timestamps
   - Internal comment indicator (admin only)

5. **TicketContext** (`dashboard/src/components/support/TicketContext.tsx`)
   - Display related agent info
   - Show recent audit logs
   - Link to full agent/audit pages

#### API Client

**Location:** `dashboard/src/services/api/support.ts`

```typescript
import { apiFetch } from './client'
import type {
  TicketCreate,
  TicketUpdate,
  CommentCreate,
  TicketResponse,
  TicketDetailResponse,
  TicketListResponse,
  CommentResponse,
} from '@/types/api'

export async function createTicket(data: TicketCreate): Promise<TicketDetailResponse> {
  return apiFetch('/api/v1/tickets', { method: 'POST', body: JSON.stringify(data) })
}

export async function listTickets(params?: {
  status?: string
  priority?: string
  category?: string
  limit?: number
  offset?: number
}): Promise<TicketListResponse> {
  const query = new URLSearchParams(params as any).toString()
  return apiFetch(`/api/v1/tickets?${query}`)
}

export async function getTicket(ticketId: string): Promise<TicketDetailResponse> {
  return apiFetch(`/api/v1/tickets/${ticketId}`)
}

export async function updateTicket(
  ticketId: string,
  data: TicketUpdate
): Promise<TicketDetailResponse> {
  return apiFetch(`/api/v1/tickets/${ticketId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function addComment(
  ticketId: string,
  data: CommentCreate
): Promise<CommentResponse> {
  return apiFetch(`/api/v1/tickets/${ticketId}/comments`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
```

### TypeScript Types

**Location:** `dashboard/src/types/api.ts` (additions)

```typescript
export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent'
export type TicketStatus = 'open' | 'in_progress' | 'waiting_customer' | 'resolved' | 'closed'
export type TicketCategory = 'technical' | 'billing' | 'feature_request' | 'bug' | 'other'

export interface TicketCreate {
  subject: string
  description: string
  priority?: TicketPriority
  category?: TicketCategory
  related_agent_id?: string
  related_audit_log_ids?: string[]
}

export interface TicketUpdate {
  subject?: string
  description?: string
  priority?: TicketPriority
  status?: TicketStatus
  category?: TicketCategory
  assigned_to_user_id?: string
}

export interface CommentCreate {
  content: string
  is_internal?: boolean
}

export interface TicketComment {
  id: string
  ticket_id: string
  user_id: string
  user_email: string
  content: string
  is_internal: boolean
  created_at: string
  updated_at: string
}

export interface SupportTicket {
  id: string
  ticket_number: string
  user_id: string
  org_id: string | null
  subject: string
  description: string
  priority: TicketPriority
  status: TicketStatus
  category: TicketCategory | null
  related_agent_id: string | null
  related_agent_name: string | null
  related_audit_log_ids: string[] | null
  assigned_to_user_id: string | null
  assigned_to_email: string | null
  comment_count: number
  created_at: string
  updated_at: string
  resolved_at: string | null
  closed_at: string | null
}

export interface TicketDetail extends SupportTicket {
  comments: TicketComment[]
  user_email: string
  org_name: string | null
}

export interface TicketListResponse {
  items: SupportTicket[]
  total: number
  limit: number
  offset: number
}
```

## Implementation Sequence

### Phase 1: Backend Foundation
1. Create SQLAlchemy models
2. Create Alembic migration
3. Define Pydantic schemas
4. Implement basic CRUD router

### Phase 2: Backend API
5. Add ticket list endpoint with filtering
6. Add ticket detail endpoint
7. Add comment endpoints
8. Add context retrieval endpoint
9. Add admin assignment capabilities

### Phase 3: Frontend Foundation
10. Create TypeScript types
11. Build API client functions
12. Add navigation item to sidebar
13. Add routes to App.tsx

### Phase 4: Frontend UI
14. Create SupportTicketsPage
15. Create TicketDetailPage
16. Create CreateTicketModal
17. Create supporting components (TicketCard, CommentThread, etc.)

### Phase 5: Integration & Polish
18. Add context display (related agents, audit logs)
19. Implement filtering and search
20. Add admin ticket management view
21. Write tests
22. Update documentation

## Security Considerations

1. **Authorization**: Users can only view/edit their own tickets unless they're admins
2. **Organization Scoping**: Tickets are scoped to organizations for multi-tenant isolation
3. **Input Validation**: All inputs validated via Pydantic schemas
4. **SQL Injection**: Protected via SQLAlchemy ORM
5. **XSS Prevention**: React automatically escapes content
6. **Internal Comments**: Only visible to admin users

## Future Enhancements

1. **File Attachments**: Allow users to upload screenshots/logs
2. **Email Notifications**: Send emails on ticket status changes
3. **SLA Tracking**: Track response times and SLA compliance
4. **Ticket Templates**: Pre-filled forms for common issues
5. **Knowledge Base Integration**: Suggest articles based on ticket content
6. **Webhooks**: Notify external systems (Slack, PagerDuty) of new tickets
7. **Ticket Merging**: Combine duplicate tickets
8. **Satisfaction Ratings**: Allow users to rate support quality

## Testing Strategy

### Backend Tests
- Unit tests for ticket CRUD operations
- Test authorization (users can't access others' tickets)
- Test filtering and pagination
- Test comment creation and retrieval
- Test context linking (agents, audit logs)

### Frontend Tests
- Component rendering tests
- Form validation tests
- API integration tests
- User interaction tests (create ticket, add comment)

## Metrics & Monitoring

Track the following metrics:
- Tickets created per day/week/month
- Average resolution time
- Tickets by priority/category
- Response time (first comment from support)
- Customer satisfaction scores (future)
- Most common ticket categories

## Documentation Updates

1. Update API documentation with new endpoints
2. Add user guide for creating tickets
3. Add admin guide for managing tickets
4. Update README with support ticket feature
