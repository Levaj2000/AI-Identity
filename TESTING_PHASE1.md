# Phase 1 Support Ticket Enhancements - Testing Guide

## Prerequisites

1. **Docker Environment Running:**
   ```bash
   docker compose up -d
   ```

2. **Database Migration Applied:**
   ```bash
   docker compose exec api alembic upgrade head
   ```

## Test Execution

### 1. Run Support Ticket Tests

```bash
# Run all support ticket tests
docker compose exec api pytest api/tests/test_support_tickets.py -v

# Run specific test
docker compose exec api pytest api/tests/test_support_tickets.py::test_create_ticket_success -v

# Run with coverage
docker compose exec api pytest api/tests/test_support_tickets.py --cov=api.app.routers.support_tickets --cov-report=term-missing
```

### 2. Run All API Tests

```bash
# Run all tests to ensure no regressions
docker compose exec api pytest api/tests/ -v
```

### 3. Manual Testing

#### Test Ticket Creation with Email
```bash
# Create a test ticket
curl -X POST http://localhost:8001/api/v1/tickets \
  -H "X-API-Key: your-test-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Test ticket for email notification",
    "description": "Testing the new email notification system.",
    "priority": "high",
    "category": "technical"
  }'
```

**Expected Results:**
- Ticket created with status 201
- `sla_due_at` field populated (24 hours from now for HIGH priority)
- Two emails sent (if RESEND_API_KEY configured):
  - Support team notification
  - Customer confirmation

#### Test Status Update Email
```bash
# Update ticket status (requires admin user)
curl -X PATCH http://localhost:8001/api/v1/tickets/{ticket_id} \
  -H "X-API-Key: admin-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved"
  }'
```

**Expected Results:**
- Ticket status updated
- `resolved_at` timestamp set
- Customer receives status update email

#### Test Comment Email
```bash
# Add a comment (as different user than ticket creator)
curl -X POST http://localhost:8001/api/v1/tickets/{ticket_id}/comments \
  -H "X-API-Key: admin-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "We are looking into this issue.",
    "is_internal": false
  }'
```

**Expected Results:**
- Comment added
- Ticket owner receives email notification
- Internal comments do NOT trigger emails

#### Test SLA Escalation Cron
```bash
# Manually trigger SLA escalation
curl -X POST http://localhost:8001/api/v1/cron/sla-escalation \
  -H "X-Internal-Key: your-internal-service-key"
```

**Expected Results:**
```json
{
  "checked": 0,
  "escalated": 0,
  "errors": [],
  "timestamp": "2026-04-30T15:00:00.000Z"
}
```

To test actual escalation:
1. Create a ticket with URGENT priority (4-hour SLA)
2. Manually update `sla_due_at` to past time in database
3. Run cron endpoint
4. Verify ticket priority escalated and email sent

## Verification Checklist

### Database Schema
- [ ] `support_tickets` table has `sla_due_at`, `sla_breached`, `escalation_count` columns
- [ ] Index `idx_tickets_sla_due` exists
- [ ] Migration applied successfully

### Email Functions
- [ ] `send_ticket_created_email` exists in `api/app/email.py`
- [ ] `send_ticket_status_update_email` exists
- [ ] `send_ticket_comment_email` exists
- [ ] `send_sla_breach_notification` exists
- [ ] All email HTML templates defined

### SLA Logic
- [ ] `api/app/sla.py` module exists
- [ ] SLA hours defined for all priorities
- [ ] `calculate_sla_due_at` function works
- [ ] `should_escalate` function works
- [ ] `escalate_priority` function works

### Router Integration
- [ ] Ticket creation sets `sla_due_at`
- [ ] Status updates trigger emails for RESOLVED/CLOSED
- [ ] Comments trigger emails (public only, not self-comments)
- [ ] SLA escalation cron registered in `main.py`

### Tests
- [ ] All test fixtures defined (`admin_user`, `admin_headers`)
- [ ] Test file has no syntax errors
- [ ] Tests cover CRUD operations
- [ ] Tests cover access control
- [ ] Tests cover comments
- [ ] Tests cover ticket number generation

## Common Issues & Solutions

### Issue: Tests fail with "No module named pytest"
**Solution:** Tests must run inside Docker container:
```bash
docker compose exec api pytest api/tests/test_support_tickets.py -v
```

### Issue: Database migration fails
**Solution:** Check if previous migrations are applied:
```bash
docker compose exec api alembic current
docker compose exec api alembic upgrade head
```

### Issue: Emails not sending
**Solution:** Check environment variables:
```bash
docker compose exec api env | grep RESEND
```
If `RESEND_API_KEY` is not set, emails will be skipped (logged but not sent).

### Issue: Type checker errors
**Solution:** These are expected false positives from SQLAlchemy ORM patterns. The code is runtime-safe.

### Issue: SLA escalation not working
**Solution:**
1. Verify internal service key is set: `INTERNAL_SERVICE_KEY`
2. Check ticket has `sla_due_at` in the past
3. Check ticket status is OPEN, IN_PROGRESS, or WAITING_CUSTOMER
4. Check `sla_breached` is False

## Performance Testing

### Load Test Ticket Creation
```bash
# Create 100 tickets
for i in {1..100}; do
  curl -X POST http://localhost:8001/api/v1/tickets \
    -H "X-API-Key: your-test-api-key" \
    -H "Content-Type: application/json" \
    -d "{\"subject\":\"Load test ticket $i\",\"description\":\"Testing performance with ticket $i\",\"priority\":\"medium\"}" &
done
wait
```

### Check SLA Query Performance
```bash
# Time the SLA escalation query
docker compose exec api python -c "
from datetime import UTC, datetime
from common.models import SupportTicket, get_db
from common.models.support_ticket import TicketStatus
import time

db = next(get_db())
start = time.time()
tickets = db.query(SupportTicket).filter(
    SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_CUSTOMER]),
    SupportTicket.sla_due_at <= datetime.now(UTC),
    SupportTicket.sla_breached == False
).all()
elapsed = time.time() - start
print(f'Found {len(tickets)} tickets in {elapsed:.3f}s')
"
```

## Success Criteria

✅ All tests pass  
✅ Database migration applies cleanly  
✅ Tickets created with SLA due times  
✅ Emails sent on ticket creation (if configured)  
✅ Emails sent on status updates  
✅ Emails sent on comments  
✅ SLA escalation cron runs without errors  
✅ No regressions in existing tests  

## Next Steps After Testing

1. **Deploy to staging environment**
2. **Monitor email delivery rates**
3. **Set up Kubernetes CronJob for SLA escalation**
4. **Update user documentation**
5. **Plan Phase 2 enhancements** (search, metrics, templates, etc.)

---

Made with Bob 🤖
