# Troubleshooting Guide - Unified Communication Platform

## Issues and Solutions

### 1. Contact Edit/Add Not Working

**Problem**: Contact modal doesn't open or save functionality doesn't work.

**Solutions**:
1. **Check Browser Console**: Open Developer Tools (F12) and check for JavaScript errors
2. **Verify Bootstrap**: Ensure Bootstrap 5 is properly loaded
3. **Check API Endpoints**: Verify `/api/add-contact` and `/api/update-contact` are accessible
4. **Database Issues**: Run database initialization script

**Debugging Steps**:
```bash
# Initialize database with sample data
cd backend
python init_db.py

# Check if Flask app is running
python run.py
```

**Manual Test**:
1. Open browser console (F12)
2. Go to Contacts page
3. Click "Add Contact" button
4. Check console for any error messages
5. Fill form and submit
6. Check network tab for API calls

### 2. Chat Not Working

**Problem**: Chat messages don't load or send functionality doesn't work.

**Solutions**:
1. **Check API Endpoints**: Verify `/api/chats` and `/api/chats/<id>/messages` are working
2. **Database Issues**: Ensure chat and message tables exist
3. **User Authentication**: Verify user is logged in

**Debugging Steps**:
```bash
# Check if chat API endpoints work
curl -X GET http://localhost:5000/api/chats
curl -X GET http://localhost:5000/api/chats/1/messages
```

**Manual Test**:
1. Open browser console (F12)
2. Go to Chat page
3. Click on a chat
4. Check console for error messages
5. Try sending a message
6. Check network tab for API calls

### 3. SMS Issues

**Problem**: SMS sends successfully but messages don't arrive.

**Expected Behavior**: 
- This is **NORMAL** for the demo version
- SMS functionality is simulated (no real SMS gateway)
- Messages are not actually sent to real phone numbers
- Success message indicates the API is working correctly

**Real Implementation**:
To implement real SMS, you would need:
1. SMS gateway provider (Twilio, Nexmo, etc.)
2. API credentials
3. Update `/api/send-sms` endpoint to use real SMS service

### 4. Phone Section Issues

**Problem**: Phone calls don't work or external calling fails.

**Solutions**:
1. **Check API Endpoints**: Verify `/api/make-external-call` is working
2. **SIP Configuration**: Ensure SIP trunk is configured
3. **Phone Number Format**: Use proper international format (+1234567890)

**Debugging Steps**:
```bash
# Test external call API
curl -X POST http://localhost:5000/api/make-external-call \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "call_type": "voice"}'
```

## Common Issues and Fixes

### Database Issues
```bash
# Reset database
cd backend
rm -f app.db  # Delete existing database
python init_db.py  # Recreate with sample data
```

### Flask App Issues
```bash
# Check if app starts
cd backend
python run.py

# Check for import errors
python -c "from app import create_app; app = create_app()"
```

### API Endpoint Issues
```bash
# Test all API endpoints
python test_functionality.py
```

## Sample Data

After running `init_db.py`, you'll have:

**Users**:
- Admin: `admin` / `admin123`
- Test User 1: `john` / `password123`
- Test User 2: `jane` / `password123`

**Sample Contacts** (for admin user):
- Alice Johnson: +1234567893
- Bob Wilson: +1234567894
- Charlie Brown: +1234567895

**Sample Chat**:
- Direct chat between admin and john with sample messages

## Browser Console Debugging

Open Developer Tools (F12) and check:

1. **Console Tab**: Look for JavaScript errors
2. **Network Tab**: Check API calls and responses
3. **Application Tab**: Check if cookies/session are set

## Expected API Responses

### Contact APIs
```json
// GET /api/contacts
{
  "success": true,
  "contacts": [
    {
      "id": 1,
      "name": "Alice Johnson",
      "phone": "+1234567893",
      "email": "alice@example.com",
      "company": "Tech Corp",
      "notes": "Software developer"
    }
  ]
}

// POST /api/add-contact
{
  "success": true,
  "contact_id": 1
}
```

### Chat APIs
```json
// GET /api/chats
{
  "success": true,
  "chats": [
    {
      "id": 1,
      "name": "Test Chat",
      "chat_type": "direct",
      "participants": [...],
      "message_count": 3
    }
  ]
}

// GET /api/chats/1/messages
[
  {
    "id": 1,
    "content": "Hello! How are you?",
    "sender": {
      "id": 1,
      "name": "Admin User",
      "username": "admin"
    },
    "created_at": "2024-01-01 12:00:00"
  }
]
```

### Phone APIs
```json
// POST /api/make-external-call
{
  "success": true,
  "call_id": "uuid-string",
  "message": "Initiating call to +1234567890 through SIP trunk"
}
```

## Contact Information

If you continue to experience issues:

1. Check the browser console for specific error messages
2. Verify all API endpoints are responding correctly
3. Ensure the database is properly initialized
4. Check that all required dependencies are installed

## Quick Fix Checklist

- [ ] Database initialized with `python init_db.py`
- [ ] Flask app running on `http://localhost:5000`
- [ ] User logged in (check session)
- [ ] Browser console shows no JavaScript errors
- [ ] Network tab shows successful API calls
- [ ] All modals open properly (Bootstrap 5)
- [ ] Toast notifications working 