# Support Ticket System - Architecture Diagram

## System Architecture

```mermaid
graph TB
    subgraph "Frontend - React Dashboard"
        A[SupportTicketsPage] --> B[TicketCard]
        A --> C[TicketFilters]
        A --> D[CreateTicketModal]
        E[TicketDetailPage] --> F[CommentThread]
        E --> G[TicketContext]
        E --> H[AddCommentForm]

        I[Sidebar] -.->|Navigate| A
        I -.->|Navigate| E
    end

    subgraph "API Layer"
        J[/api/v1/tickets]
        K[/api/v1/tickets/:id]
        L[/api/v1/tickets/:id/comments]
        M[/api/v1/tickets/:id/context]
    end

    subgraph "Backend - FastAPI"
        N[support_tickets.py Router]
        O[Auth Middleware]
        P[Ticket Service Logic]
    end

    subgraph "Database - PostgreSQL"
        Q[(support_tickets)]
        R[(ticket_comments)]
        S[(users)]
        T[(organizations)]
        U[(agents)]
        V[(audit_log)]
    end

    A -->|HTTP GET| J
    D -->|HTTP POST| J
    E -->|HTTP GET| K
    E -->|HTTP PATCH| K
    H -->|HTTP POST| L
    E -->|HTTP GET| M

    J --> N
    K --> N
    L --> N
    M --> N

    N --> O
    O --> P

    P --> Q
    P --> R
    P --> S
    P --> T
    P --> U
    P --> V

    Q -.->|FK| S
    Q -.->|FK| T
    Q -.->|FK| U
    R -.->|FK| Q
    R -.->|FK| S
```

## Data Flow - Create Ticket

```mermaid
sequenceDiagram
    participant User
    participant Dashboard
    participant API
    participant DB
    participant Email

    User->>Dashboard: Click "Create Ticket"
    Dashboard->>User: Show CreateTicketModal
    User->>Dashboard: Fill form & submit
    Dashboard->>API: POST /api/v1/tickets
    API->>API: Validate auth token
    API->>API: Validate input data
    API->>DB: Generate ticket_number
    API->>DB: INSERT support_ticket
    API->>DB: Link to org/agent if provided
    DB-->>API: Return ticket record
    API->>Email: Send notification (optional)
    API-->>Dashboard: Return TicketDetailResponse
    Dashboard->>User: Show success & redirect
    Dashboard->>Dashboard: Navigate to ticket detail
```

## Data Flow - View & Comment

```mermaid
sequenceDiagram
    participant User
    participant Dashboard
    participant API
    participant DB

    User->>Dashboard: Click ticket in list
    Dashboard->>API: GET /api/v1/tickets/:id
    API->>API: Verify user owns ticket or is admin
    API->>DB: SELECT ticket with joins
    API->>DB: SELECT comments for ticket
    API->>DB: SELECT related agent/audit logs
    DB-->>API: Return full ticket data
    API-->>Dashboard: Return TicketDetailResponse
    Dashboard->>User: Display ticket details

    User->>Dashboard: Type comment & submit
    Dashboard->>API: POST /api/v1/tickets/:id/comments
    API->>DB: INSERT ticket_comment
    API->>DB: UPDATE ticket.updated_at
    DB-->>API: Return comment record
    API-->>Dashboard: Return CommentResponse
    Dashboard->>Dashboard: Append to comment thread
```

## Component Hierarchy

```mermaid
graph TD
    A[App.tsx] --> B[DashboardLayout]
    B --> C[Sidebar]
    B --> D[Main Content Area]

    D --> E[SupportTicketsPage]
    D --> F[TicketDetailPage]

    E --> G[TicketFilters]
    E --> H[CreateTicketModal]
    E --> I[TicketCard List]
    I --> J[TicketCard]

    F --> K[Ticket Header]
    F --> L[Ticket Body]
    F --> M[CommentThread]
    F --> N[TicketContext]
    F --> O[AddCommentForm]

    M --> P[CommentItem]
    N --> Q[RelatedAgent]
    N --> R[RelatedAuditLogs]

    C -.->|Link| E
    J -.->|Navigate| F
```

## Database Relationships

```mermaid
erDiagram
    USERS ||--o{ SUPPORT_TICKETS : creates
    USERS ||--o{ TICKET_COMMENTS : writes
    USERS ||--o{ SUPPORT_TICKETS : "assigned to"
    ORGANIZATIONS ||--o{ SUPPORT_TICKETS : owns
    AGENTS ||--o{ SUPPORT_TICKETS : "related to"
    SUPPORT_TICKETS ||--o{ TICKET_COMMENTS : contains

    USERS {
        uuid id PK
        string email
        string role
        uuid org_id FK
    }

    ORGANIZATIONS {
        uuid id PK
        string name
        string tier
    }

    AGENTS {
        uuid id PK
        uuid user_id FK
        uuid org_id FK
        string name
        string status
    }

    SUPPORT_TICKETS {
        uuid id PK
        string ticket_number UK
        uuid user_id FK
        uuid org_id FK
        string subject
        text description
        string priority
        string status
        string category
        uuid related_agent_id FK
        jsonb related_audit_log_ids
        uuid assigned_to_user_id FK
        timestamp created_at
        timestamp updated_at
    }

    TICKET_COMMENTS {
        uuid id PK
        uuid ticket_id FK
        uuid user_id FK
        text content
        boolean is_internal
        timestamp created_at
    }
```

## State Management

```mermaid
stateDiagram-v2
    [*] --> Open: Ticket Created
    Open --> InProgress: Admin starts work
    InProgress --> WaitingCustomer: Admin requests info
    WaitingCustomer --> InProgress: Customer responds
    InProgress --> Resolved: Issue fixed
    Resolved --> Closed: Customer confirms
    Resolved --> InProgress: Customer reopens
    Open --> Closed: Duplicate/Invalid
    InProgress --> Closed: Cannot reproduce
    Closed --> [*]

    note right of Open
        Customer can create
        and view ticket
    end note

    note right of InProgress
        Admin assigned
        Working on solution
    end note

    note right of WaitingCustomer
        Awaiting customer
        response/info
    end note

    note right of Resolved
        Solution provided
        Awaiting confirmation
    end note

    note right of Closed
        Ticket archived
        No further action
    end note
```

## Security Model

```mermaid
graph TB
    A[User Request] --> B{Authenticated?}
    B -->|No| C[401 Unauthorized]
    B -->|Yes| D{Has API Key?}
    D -->|No| C
    D -->|Yes| E{Ticket Access Check}

    E --> F{Is Admin?}
    F -->|Yes| G[Full Access]

    F -->|No| H{Owns Ticket?}
    H -->|Yes| I[Read/Write Own Ticket]
    H -->|No| J[403 Forbidden]

    E --> K{Same Org?}
    K -->|Yes| L{Org Role Check}
    K -->|No| J

    L -->|Owner/Admin| G
    L -->|Member| I

    G --> M[Can View All Tickets]
    G --> N[Can Assign Tickets]
    G --> O[Can See Internal Comments]

    I --> P[Can View Own Tickets]
    I --> Q[Can Add Comments]
    I --> R[Can Update Status]
```

## Integration Points

```mermaid
graph LR
    A[Support Ticket System] --> B[User Management]
    A --> C[Organization System]
    A --> D[Agent Registry]
    A --> E[Audit Log System]
    A --> F[Email Service]

    B -.->|User ID| A
    B -.->|User Role| A

    C -.->|Org ID| A
    C -.->|Org Tier| A

    D -.->|Agent ID| A
    D -.->|Agent Name| A

    E -.->|Audit Log IDs| A
    E -.->|Context Data| A

    F -.->|Notifications| A

    style A fill:#A6DAFF
    style B fill:#e1f5ff
    style C fill:#e1f5ff
    style D fill:#e1f5ff
    style E fill:#e1f5ff
    style F fill:#e1f5ff
```

## API Request/Response Flow

```mermaid
graph LR
    subgraph "Client Side"
        A[React Component]
        B[API Client Function]
        C[Type Definitions]
    end

    subgraph "Network"
        D[HTTP Request]
        E[HTTP Response]
    end

    subgraph "Server Side"
        F[FastAPI Router]
        G[Auth Middleware]
        H[Pydantic Validation]
        I[Business Logic]
        J[Database Query]
    end

    A -->|Call| B
    B -->|Uses| C
    B -->|Send| D
    D --> F
    F --> G
    G --> H
    H --> I
    I --> J
    J --> I
    I --> H
    H --> F
    F -->|Return| E
    E --> B
    B -->|Parse| C
    C --> A
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Client Browser"
        A[React SPA]
    end

    subgraph "Vercel CDN"
        B[Static Assets]
        C[Dashboard Bundle]
    end

    subgraph "Google Cloud Platform"
        D[Cloud Run - API]
        E[Cloud SQL - PostgreSQL]
        F[Cloud Storage]
    end

    subgraph "External Services"
        G[SendGrid Email]
        H[Sentry Monitoring]
    end

    A -->|HTTPS| B
    A -->|HTTPS| C
    A -->|API Calls| D
    D -->|Query| E
    D -->|Store Files| F
    D -->|Send Email| G
    D -->|Error Tracking| H

    style A fill:#A6DAFF
    style D fill:#A6DAFF
    style E fill:#A6DAFF
