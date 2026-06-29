# services/session_manager.py
# Manages in-memory session storage

sessions = {}

def create_session(session_obj):
    """Store a session object and return its session_id."""
    sessions[session_obj.session_id] = session_obj
    return session_obj.session_id

def get_session(session_id):
    """Retrieve a session by its ID."""
    return sessions.get(session_id)

def stop_session(session_id):
    """Stop a session if it exists."""
    sess = get_session(session_id)
    if sess:
        sess.stop()
        return True
    return False

def get_all_sessions():
    """Return all sessions (for debugging or management)."""
    return sessions